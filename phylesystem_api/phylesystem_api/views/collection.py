import json
import logging
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
    fetch_doc,
    commit_doc_and_trigger_push,
    get_parent_sha,
    get_commit_message,
    get_owner_id,
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
        raise400(msg)
    if len(errors) > 0:
        msg = "JSON payload failed validation with {nerrors} errors:\n{errors}"
        msg = msg.format(nerrors=len(errors), errors="\n  ".join(errors))
        raise400(msg)
    return collection_obj, errors, collection_adaptor


@view_config(route_name="create_collection", renderer="json", request_method="OPTIONS")
@view_config(route_name="collection_CORS_preflight", renderer="json")
def collection_CORS_preflight(request):
    api_utils.raise_on_CORS_preflight(request)


def is_valid_collection_id(doc_id):
    return bool(COLLECTION_ID_PATTERN.match(doc_id))


@view_config(route_name="fetch_collection", renderer="json")
def fetch_collection(request):
    # NB - This method does not require authentication!
    collection_id = request.matchdict["collection_id"]
    result = fetch_doc(
        request,
        doc_id=collection_id,
        doc_store=api_utils.get_tree_collection_store(request),
        doc_type_name="collection",
        doc_id_validator=is_valid_collection_id,
        add_version_history=True,
    )
    return add_collection_specific_fields(request, collection_id, result)


def add_collection_specific_fields(request, collection_id, result):
    collection_json = result["data"]
    # Add commentHTML to result JSON
    try:
        comment_html = api_utils.markdown_to_html(
            collection_json["description"], open_links_in_new_window=True
        )
    except:
        comment_html = ""
    result["commentHTML"] = comment_html

    # Add the url field to the stored JSON
    base_url = api_utils.get_collections_api_base_url(request)
    collection_json["url"] = "{b}/v2/collection/{i}".format(b=base_url, i=collection_id)

    # Add the lastModified field to the result JSON
    version_history = result.get("versionHistory")
    if version_history:
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


@view_config(route_name="create_collection", renderer="json", request_method="POST")
def create_collection(request):
    auth_info = api_utils.auth_and_not_read_only(request)
    commit_msg = get_commit_message(request)
    # fetch and parse the JSON payload, if any
    (
        collection_obj,
        collection_errors,
        collection_adapter,
    ) = __extract_and_validate_collection(request, request.params)
    if collection_obj is None:
        msg = "collection JSON expected for HTTP method {}".format(request.method)
        raise400(msg)

    owner_id = get_owner_id(request, auth_info)

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

    def coll_commit_fn(doc, doc_id, auth_info, parent_sha, merged_sha, commit_msg):
        return docstore.add_new_collection(
            owner_id, doc, auth_info, doc_id, commit_msg=commit_msg
        )

    return commit_doc_and_trigger_push(
        request,
        commit_fn=coll_commit_fn,
        doc=collection_obj,
        doc_id=collection_id,
        doc_type_name="collection",
        auth_info=auth_info,
        commit_msg=commit_msg,
    )


@view_config(route_name="update_collection", renderer="json")
def update_collection(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.collection')
    # NB - This method requires authentication!
    r_auth_info = api_utils.auth_and_not_read_only(request)
    _LOG.debug("COLLECTION: update_collection")
    owner_id = get_owner_id(request, r_auth_info)

    collection_id = request.matchdict["collection_id"]
    if not is_valid_collection_id(collection_id):
        msg = "invalid collection ID ({}) provided".format(collection_id)
        raise400(msg)

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
    docstore = api_utils.get_tree_collection_store(request)

    def update_collection_fn(
        doc, doc_id, auth_info, parent_sha, merged_sha, commit_msg
    ):
        return doc_id, docstore.update_existing_collection(
            owner_id,
            doc_id,
            doc,
            auth_info,
            parent_sha,
            merged_sha,
            commit_msg=commit_msg,
        )

    r_parent_sha = find_in_request(request, "starting_commit_SHA", None)
    r_merged_sha = None  # TODO: find_in_request(request, '???', None)
    r_commit_msg = get_commit_message(request)
    blob = commit_doc_and_trigger_push(
        request,
        commit_fn=update_collection_fn,
        doc=collection_obj,
        doc_id=collection_id,
        doc_type_name="collection",
        auth_info=r_auth_info,
        parent_sha=r_parent_sha,
        merged_sha=r_merged_sha,
        commit_msg=r_commit_msg,
    )
    blob["versionHistory"] = docstore.get_version_history_for_doc_id(collection_id)
    return blob


@view_config(route_name="delete_collection", renderer="json")
def delete_collection(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.collection')
    # NB - This method requires authentication!
    auth_info = api_utils.auth_and_not_read_only(request)
    collection_id = request.matchdict["collection_id"]
    if not is_valid_collection_id(collection_id):
        msg = "invalid collection ID ({}) provided".format(collection_id)
        raise400(msg)
    commit_msg = get_commit_message(request)

    # remove this collection from the docstore
    docstore = api_utils.get_tree_collection_store(request)
    parent_sha = get_parent_sha(request)
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
