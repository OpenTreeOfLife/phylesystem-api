import logging

from peyotl.amendments import AMENDMENT_ID_PATTERN
from peyotl.amendments.validation import validate_amendment

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
    HTTPException,
    HTTPBadRequest,
)
from pyramid.view import view_config

import phylesystem_api.api_utils as api_utils
from phylesystem_api.api_utils import (
    extract_json_from_http_call,
    raise400,
    fetch_doc,
    commit_doc_and_trigger_push,
    get_parent_sha,
    get_commit_message,
)

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


def is_valid_amendment_id(doc_id):
    return bool(AMENDMENT_ID_PATTERN.match(doc_id))


@view_config(route_name="fetch_amendment", renderer="json")
def fetch_amendment(request):
    # NB - This method does not require authentication!
    amendment_id = request.matchdict["amendment_id"]
    return fetch_doc(
        request,
        doc_id=amendment_id,
        doc_store=api_utils.get_taxonomic_amendment_store(request),
        doc_type_name="amendment",
        doc_id_validator=is_valid_amendment_id,
        add_version_history=True,
    )


@view_config(route_name="create_amendment", renderer="json", request_method="POST")
def create_amendment(request, **kwargs):
    _LOG.debug("Begin create ammendemt")
    auth_info = api_utils.auth_and_not_read_only(request)
    commit_msg = get_commit_message(request)
    # fetch and parse the JSON payload, if any
    (
        amendment_obj,
        amendment_errors,
        amendment_adapter,
    ) = __extract_and_validate_amendment(request, kwargs)
    if amendment_obj is None:
        msg = "amendment JSON expected for HTTP method {}".format(request.method)
        raise400(msg)

    # N.B. add_new_amendment below takes care of minting new ottids,
    # assigning them to new taxa, and returning a per-taxon mapping to the
    # caller. It will assign the new amendment id accordingly!
    docstore = api_utils.get_taxonomic_amendment_store(request)

    def amend_commit_fn(doc, doc_id, auth_info, commit_msg):
        return docstore.add_new_amendment(
            doc, auth_info=auth_info, commit_msg=commit_msg
        )

    return commit_doc_and_trigger_push(
        request,
        commit_fn=amend_commit_fn,
        doc=amendment_obj,
        doc_id=None,
        doc_type_name="amendment",
        auth_info=auth_info,
        commit_msg=commit_msg,
    )


@view_config(route_name="update_amendment", renderer="json")
def update_amendment(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')
    amendment_id = request.matchdict["amendment_id"]
    if not is_valid_amendment_id(amendment_id):
        raise400("invalid amendment ID ({}) provided".format(amendment_id))
    r_auth_info = api_utils.auth_and_not_read_only(request)
    r_commit_msg = get_commit_message(request)
    # fetch and parse the JSON payload, if any
    (
        amendment_obj,
        amendment_errors,
        amendment_adapter,
    ) = __extract_and_validate_amendment(request, request.params)
    if amendment_obj is None:
        msg = "amendment JSON expected for HTTP method {}".format(request.method)
        raise400(msg)

    # update an existing amendment with the data provided
    # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.PUT')
    # submit new json for this id, and read the results
    r_parent_sha = get_parent_sha(request)
    r_merged_sha = None  # TODO: find_in_request(request, '???', None)
    docstore = api_utils.get_taxonomic_amendment_store(request)

    def update_amendment_fn(doc, doc_id, auth_info, parent_sha, merged_sha, commit_msg):
        return doc_id, docstore.update_existing_amendment(
            doc_id,
            doc,
            auth_info,
            parent_sha,
            merged_sha,
            commit_msg=commit_msg,
        )

    blob = commit_doc_and_trigger_push(
        request,
        commit_fn=update_amendment_fn,
        doc=amendment_obj,
        doc_id=amendment_id,
        doc_type_name="amendment",
        auth_info=r_auth_info,
        parent_sha=r_parent_sha,
        merged_sha=r_merged_sha,
        commit_msg=r_commit_msg,
    )
    return blob


@view_config(route_name="delete_amendment", renderer="json")
def delete_amendment(request):
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')
    amendment_id = request.matchdict.get["amendment_id"]
    if not is_valid_amendment_id(amendment_id):
        raise400("invalid amendment ID ({}) provided".format(amendment_id))
    r_auth_info = api_utils.auth_and_not_read_only(request)
    r_parent_sha = get_parent_sha(request)
    r_commit_msg = get_commit_message(request)
    docstore = api_utils.get_taxonomic_amendment_store(request)

    def del_amendment_fn(doc, doc_id, auth_info, parent_sha, merged_sha, commit_msg):
        return doc_id, docstore.delete_amendment(
            doc_id,
            auth_info,
            parent_sha,
            commit_msg=commit_msg,
        )

    blob = commit_doc_and_trigger_push(
        request,
        commit_fn=del_amendment_fn,
        doc=None,
        doc_id=amendment_id,
        doc_type_name="amendment",
        auth_info=r_auth_info,
        parent_sha=r_parent_sha,
        merged_sha=None,
        commit_msg=r_commit_msg,
    )
    return blob
