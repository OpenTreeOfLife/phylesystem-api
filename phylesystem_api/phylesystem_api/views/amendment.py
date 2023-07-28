import traceback
import sys
from pyramid.view import view_config

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
    HTTPException,
    HTTPBadRequest,
)
from peyotl.phylesystem.git_workflows import GitWorkflowError
import phylesystem_api.api_utils as api_utils
from phylesystem_api.api_utils import (
    find_in_request,
    extract_json_from_http_call,
    raise400,
    raise404,
)
import json
import logging

from peyotl.amendments import AMENDMENT_ID_PATTERN
from peyotl.amendments.validation import validate_amendment


_LOG = logging.getLogger("phylesystem_api")


def __extract_and_validate_amendment(request, kwargs):

    try:
        amendment_obj = extract_json_from_http_call(
            request, data_field_name="json", request_params=kwargs
        )
    except HTTPException:
        # payload not found
        return None, None, None
    try:
        errors, amendment_adaptor = validate_amendment(amendment_obj)
    except HTTPException:
        raise
    except Exception as err:
        # _LOG.exception('JSON payload failed validation (reporting err.msg)')
        # pprint(err)
        try:
            msg = getattr(err, "msg", "No message found")
        except:
            msg = str(err)
        raise HTTPBadRequest(body=msg)
    if len(errors) > 0:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        msg = "JSON payload failed validation with {nerrors} errors:\n{errors}".format(
            nerrors=len(errors), errors="\n  ".join(errors)
        )
        # _LOG.exception(msg)
        raise HTTPBadRequest(body=msg)
    return amendment_obj, errors, amendment_adaptor


@view_config(route_name="create_amendment", renderer="json", request_method="OPTIONS")
@view_config(route_name="amendment_CORS_preflight", renderer="json")
def amendment_CORS_preflight(request):
    api_utils.raise_on_CORS_preflight(request)


@view_config(route_name="create_amendment", renderer="json", request_method="POST")
def create_amendment(request, **kwargs):
    _LOG.debug("Begin create ammendemt")
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')

    # this method requires authentication
    auth_info = api_utils.authenticate(request)

    # gather any user-provided git-commit message
    try:
        commit_msg = find_in_request(request, "commit_msg", "")
        if commit_msg.strip() == "":
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    api_utils.raise_if_read_only()
    # fetch and parse the JSON payload, if any
    (
        amendment_obj,
        amendment_errors,
        amendment_adapter,
    ) = __extract_and_validate_amendment(request, kwargs)
    if amendment_obj is None:
        msg = "amendment JSON expected for HTTP method {}".format(request.method)
        raise400(msg)

    # Create a new amendment with the data provided
    # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.POST')
    # submit the json and proposed id (if any), and read the results
    docstore = api_utils.get_taxonomic_amendment_store(request)
    # N.B. add_new_amendment below takes care of minting new ottids,
    # assigning them to new taxa, and returning a per-taxon mapping to the
    # caller. It will assign the new amendment id accordingly!
    try:
        r = docstore.add_new_amendment(amendment_obj, auth_info, commit_msg=commit_msg)
        new_amendment_id, commit_return = r
    except GitWorkflowError as err:
        raise HTTPBadRequest(body=err.msg)
    except:
        raise HTTPBadRequest(body=traceback.format_exc())
    if commit_return["error"] != 0:
        # _LOG.debug('add_new_amendment failed with error code')
        raise HTTPBadRequest(body=json.dumps(commit_return))
    _LOG.debug("create ammendemt deferred_push_to_gh_call")
    api_utils.deferred_push_to_gh_call(
        request,
        new_amendment_id,
        doc_type="amendment",
        auth_token=auth_info["auth_token"],
    )
    return commit_return


@view_config(route_name="fetch_amendment", renderer="json")
def fetch_amendment(request):
    # NB - This method does not require authentication!
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')
    amendment_id = request.matchdict["amendment_id"]
    if not AMENDMENT_ID_PATTERN.match(amendment_id):
        msg = "invalid amendment ID ({}) provided".format(amendment_id)
        raise400(msg)

    # fetch the current amendment JSON
    # _LOG.debug('GET /v2/amendment/{}'.format(str(amendment_id)))
    try:
        parent_sha = find_in_request(request, "starting_commit_SHA", None)
    except:
        # probably a simple request w/o JSON payload
        parent_sha = None
    # _LOG.debug('parent_sha = {}'.format(parent_sha))
    # return the correct nexson of study_id, using the specified view
    amendments = api_utils.get_taxonomic_amendment_store(request)
    try:
        r = amendments.return_doc(
            amendment_id, commit_sha=parent_sha, return_WIP_map=True
        )
    except:
        raise404("Amendment '{}' GET failure".format(amendment_id))
    try:
        amendment_json, head_sha, wip_map = r
        ## if returning_full_study:  # TODO: offer bare vs. full output (w/ history, etc)
        version_history = amendments.get_version_history_for_doc_id(amendment_id)
    except:
        # _LOG.exception('GET failed')
        e = sys.exc_info()[0]
        raise HTTPBadRequest(body=e)
    if not amendment_json:
        raise404("Amendment '{s}' has no JSON data!".format(s=amendment_id))

    try:
        external_url = amendments.get_public_url(amendment_id)
    except:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('amendment {} not found in external_url'.format(amendment))
        external_url = "NOT FOUND"
    result = {
        "sha": head_sha,
        "data": amendment_json,
        "branch2sha": wip_map,
        "external_url": external_url,
    }
    if version_history:
        result["versionHistory"] = version_history
    return result


@view_config(route_name="update_amendment", renderer="json")
def update_amendment(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')
    amendment_id = request.matchdict["amendment_id"]
    if not AMENDMENT_ID_PATTERN.match(amendment_id):
        msg = "invalid amendment ID ({}) provided".format(amendment_id)
        raise400(msg)

    # this method requires authentication
    auth_info = api_utils.authenticate(request)

    # gather any user-provided git-commit message
    try:
        commit_msg = find_in_request(request, "commit_msg", "")
        if commit_msg.strip() == "":
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    # fetch and parse the JSON payload, if any
    (
        amendment_obj,
        amendment_errors,
        amendment_adapter,
    ) = __extract_and_validate_amendment(request, request.params)
    if amendment_obj is None:
        msg = "amendment JSON expected for HTTP method {}".format(request.method)
        raise400(msg)

    api_utils.raise_if_read_only()

    # update an existing amendment with the data provided
    # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.PUT')
    # submit new json for this id, and read the results
    parent_sha = find_in_request(request, "starting_commit_SHA", None)
    merged_sha = None  # TODO: find_in_request(request, '???', None)
    docstore = api_utils.get_taxonomic_amendment_store(request)
    try:
        r = docstore.update_existing_amendment(
            amendment_id,
            amendment_obj,
            auth_info,
            parent_sha,
            merged_sha,
            commit_msg=commit_msg,
        )
        commit_return = r
    except GitWorkflowError as err:
        raise HTTPBadRequest(body=err.msg)
    except:
        raise HTTPBadRequest(body=traceback.format_exc())

    # check for 'merge needed'?
    mn = commit_return.get("merge_needed")
    if (mn is not None) and (not mn):
        api_utils.deferred_push_to_gh_call(
            request,
            amendment_id,
            doc_type="amendment",
            auth_token=auth_info["auth_token"],
        )
    return commit_return


@view_config(route_name="delete_amendment", renderer="json")
def delete_amendment(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')
    amendment_id = request.matchdict.get["amendment_id"]
    if not AMENDMENT_ID_PATTERN.match(amendment_id):
        msg = "invalid amendment ID ({}) provided".format(amendment_id)
        body = {
            "error": 1,
            "description": msg,
        }
        raise HTTPBadRequest(body=json.dumps(body))

    # this method requires authentication
    auth_info = api_utils.authenticate(request)

    # gather any user-provided git-commit message
    try:
        commit_msg = find_in_request(request, "commit_msg", "")
        if commit_msg.strip() == "":
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    api_utils.raise_if_read_only()

    # remove this amendment from the docstore
    # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.POST')
    docstore = api_utils.get_taxonomic_amendment_store(request)
    parent_sha = find_in_request(request, "starting_commit_SHA")
    if parent_sha is None:
        raise HTTPBadRequest(
            body='Expecting a "starting_commit_SHA" argument with the SHA of the parent'
        )
    try:
        x = docstore.delete_amendment(
            amendment_id, auth_info, parent_sha, commit_msg=commit_msg
        )
        if x.get("error") == 0:
            api_utils.deferred_push_to_gh_call(
                request, None, doc_type="amendment", auth_token=auth_info["auth_token"]
            )
        return x
    except GitWorkflowError as err:
        raise HTTPBadRequest(body=err.msg)
    except:
        # _LOG.exception('Unknown error in amendment deletion')
        raise HTTPBadRequest(body=traceback.format_exc())
