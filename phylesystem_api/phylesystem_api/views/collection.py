import json
import logging
import sys
import traceback

from peyotl.collections_store import COLLECTION_ID_PATTERN
from peyotl.collections_store.validation import validate_collection
from peyotl.phylesystem.git_workflows import GitWorkflowError

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
    HTTPException,
    HTTPBadRequest,
)
from pyramid.view import view_config

import phylesystem_api.api_utils as api_utils
from phylesystem_api.api_utils import (
    find_in_request,
    extract_json_from_http_call,
    raise400,
    raise404,
)

_LOG = logging.getLogger("phylesystem_api")


def __extract_and_validate_collection(request, request_params):
    try:
        collection_obj = extract_json_from_http_call(
            request, data_field_name="json", request_params=request_params
        )
    except HTTPException:
        # payload not found
        return None, None, None
    try:
        errors, collection_adaptor = validate_collection(collection_obj)
    except HTTPException:
        _LOG.exception("JSON payload failed validation (raising HTTP response)")
        raise
    except Exception as err:
        _LOG.exception("JSON payload failed validation (reporting err.msg)")
        try:
            msg = getattr(err, "msg", "No message found")
        except:
            msg = str(err)
        raise HTTPBadRequest(msg)
    if len(errors) > 0:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        msg = "JSON payload failed validation with {nerrors} errors:\n{errors}".format(
            nerrors=len(errors), errors="\n  ".join(errors)
        )
        # _LOG.exception(msg)
        raise HTTPBadRequest(msg)
    return collection_obj, errors, collection_adaptor


@view_config(route_name="create_collection", renderer="json", request_method="OPTIONS")
@view_config(route_name="collection_CORS_preflight", renderer="json")
def collection_CORS_preflight(request):
    api_utils.raise_on_CORS_preflight(request)


@view_config(route_name="create_collection", renderer="json", request_method="POST")
def create_collection(request):
    # gather any user-provided git-commit message
    try:
        commit_msg = find_in_request(request, "commit_msg", "")
        if commit_msg.strip() == "":
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None
    auth_info = api_utils.auth_and_not_read_only(request)

    # fetch and parse the JSON payload, if any
    (
        collection_obj,
        collection_errors,
        collection_adapter,
    ) = __extract_and_validate_collection(request, request.params)
    if collection_obj is None:
        msg = "collection JSON expected for HTTP method {}".format(request.method)
        raise400(msg)

    owner_id = auth_info.get("login", None)
    if owner_id is None:
        msg = "no GitHub userid found for HTTP method {}".format(
            request.env.request_method
        )
        raise400(msg)

    # try to extract a usable collection ID from the JSON payload (confirm owner_id against above)
    url = collection_obj.get("url", None)
    if url is None:
        raise400("no collection URL provided in query string or JSON payload")
    try:
        collection_id = url.split("/collection/")[1]
    except:
        raise404("invalid URL, no collection id found: {}".format(url))
    try:
        assert collection_id.split("/")[0] == owner_id
    except:
        # _LOG.exception('{} failed'.format(request.env.request_method))
        raise404("collection URL in JSON doesn't match logged-in user: {}".format(url))

    # Create a new collection with the data provided
    # submit the json and proposed id (if any), and read the results
    docstore = api_utils.get_tree_collection_store(request)
    try:
        r = docstore.add_new_collection(
            owner_id, collection_obj, auth_info, collection_id, commit_msg=commit_msg
        )
        new_collection_id, commit_return = r
    except GitWorkflowError as err:
        raise400(str(err))
    except:
        raise HTTPBadRequest(traceback.format_exc())
    if commit_return["error"] != 0:
        # _LOG.debug('add_new_collection failed with error code')
        raise HTTPBadRequest(json.dumps(commit_return))
    api_utils.deferred_push_to_gh_call(
        request,
        new_collection_id,
        doc_type="collection",
        auth_token=auth_info["auth_token"],
    )
    return commit_return


@view_config(route_name="fetch_collection", renderer="json")
def fetch_collection(request):
    # NB - This method does not require authentication!
    # _LOG = api_utils.get_logger(request, 'ot_api.collection')
    collection_id = request.matchdict["collection_id"]
    if not COLLECTION_ID_PATTERN.match(collection_id):
        msg = "invalid collection ID ({}) provided".format(collection_id)
        raise400(msg)

    # gather details to return with the JSON core document
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    # _LOG.debug('parent_sha = {}'.format(parent_sha))
    # return the correct nexson of study_id, using the specified view
    collections = api_utils.get_tree_collection_store(request)
    try:
        r = collections.return_doc(
            collection_id, commit_sha=parent_sha, return_WIP_map=True
        )
    except:
        raise404("Collection '{}' GET failure".format(collection_id))
    try:
        collection_json, head_sha, wip_map = r
        ## if returning_full_study:  # TODO: offer bare vs. full output (w/ history, etc)
        version_history = collections.get_version_history_for_doc_id(collection_id)
        try:
            # pre-render internal description (assumes markdown!)
            comment_html = api_utils.markdown_to_html(
                collection_json["description"], open_links_in_new_window=True
            )
        except:
            comment_html = ""
    except:
        # _LOG.exception('GET failed')
        e = sys.exc_info()[0]
        raise HTTPBadRequest(e)
    if not collection_json:
        raise404("Collection '{s}' has no JSON data!".format(s=collection_id))
    # add/restore the url field (using the visible fetch URL)
    base_url = api_utils.get_collections_api_base_url(request)
    collection_json["url"] = "{b}/v2/collection/{i}".format(b=base_url, i=collection_id)
    try:
        external_url = collections.get_public_url(collection_id)
    except:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('collection {} not found in external_url'.format(collection))
        external_url = "NOT FOUND"
    result = {
        "sha": head_sha,
        "data": collection_json,
        "branch2sha": wip_map,
        "commentHTML": comment_html,
        "external_url": external_url,
    }
    if version_history:
        result["versionHistory"] = version_history

        # reckon and add 'lastModified' property, based on commit history?
        latest_commit = version_history[0]
        last_modified = {
            "author_name": latest_commit.get("author_name"),
            "relative_date": latest_commit.get("relative_date"),
            "display_date": latest_commit.get("date"),
            "ISO_date": latest_commit.get("date_ISO_8601"),
            "sha": latest_commit.get("id"),  # this is the commit hash
        }
        result["lastModified"] = last_modified
    return result


@view_config(route_name="update_collection", renderer="json")
def update_collection(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.collection')
    # NB - This method requires authentication!
    auth_info = api_utils.auth_and_not_read_only(request)
    _LOG.debug("COLLECTION: update_collection")
    _LOG.debug("COLLECTION: auth_info {}".format(auth_info))
    owner_id = auth_info.get("login", None)

    collection_id = request.matchdict["collection_id"]
    if not COLLECTION_ID_PATTERN.match(collection_id):
        msg = "invalid collection ID ({}) provided".format(collection_id)
        raise400(msg)
    try:
        commit_msg = find_in_request(request, "commit_msg", "")
        if commit_msg.strip() == "":
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    # fetch and parse the JSON payload, if any
    (
        collection_obj,
        collection_errors,
        collection_adapter,
    ) = __extract_and_validate_collection(request, request.params)
    if collection_obj is None:
        msg = "collection JSON expected for HTTP method {}".format(request.method)
        raise400(msg)

    # submit new json for this id, and read the results
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    merged_sha = None  # TODO: find_in_request(request, '???', None)
    docstore = api_utils.get_tree_collection_store(request)
    try:
        r = docstore.update_existing_collection(
            owner_id,
            collection_id,
            collection_obj,
            auth_info,
            parent_sha,
            merged_sha,
            commit_msg=commit_msg,
        )
        commit_return = r
    except GitWorkflowError as err:
        raise HTTPBadRequest(err.msg)
    except:
        raise HTTPBadRequest(traceback.format_exc())

    # check for 'merge needed'?
    mn = commit_return.get("merge_needed")
    if (mn is not None) and (not mn):
        api_utils.deferred_push_to_gh_call(
            request,
            collection_id,
            doc_type="collection",
            auth_token=auth_info["auth_token"],
        )
    # Add updated commit history to the blob
    commit_return["versionHistory"] = docstore.get_version_history_for_doc_id(
        collection_id
    )
    return commit_return


@view_config(route_name="delete_collection", renderer="json")
def delete_collection(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.collection')
    # NB - This method requires authentication!
    auth_info = api_utils.auth_and_not_read_only(request)

    collection_id = request.matchdict["collection_id"]
    if not COLLECTION_ID_PATTERN.match(collection_id):
        msg = "invalid collection ID ({}) provided".format(collection_id)
        raise400(msg)

    try:
        commit_msg = find_in_request(request, "commit_msg", "")
        if commit_msg.strip() == "":
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    # remove this collection from the docstore
    docstore = api_utils.get_tree_collection_store(request)
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    if parent_sha is None:
        raise HTTPBadRequest(
            'Expecting a "starting_commit_SHA" argument with the SHA of the parent'
        )
    try:
        x = docstore.delete_collection(
            collection_id, auth_info, parent_sha, commit_msg=commit_msg
        )
        if x.get("error") == 0:
            api_utils.deferred_push_to_gh_call(
                request, None, doc_type="collection", auth_token=auth_info["auth_token"]
            )
        return x
    except GitWorkflowError as err:
        raise HTTPBadRequest(err.msg)
    except:
        raise400("Unknown error in collection deletion")
