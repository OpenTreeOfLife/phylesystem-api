from pyramid.view import view_config
# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
                                    HTTPException,
                                    HTTPOk,
                                    HTTPError,
                                    HTTPNotFound, 
                                    HTTPBadRequest,
                                    HTTPInternalServerError,
                                   )
from peyotl.api import OTI
import phylesystem_api.api_utils as api_utils
import json

from peyotl.amendments import AMENDMENT_ID_PATTERN
from peyotl.amendments.validation import validate_amendment
def _raise_HTTP_from_msg(msg):
    raise HTTPBadRequest(body=json.dumps({"error": 1, "description": msg}))

def _raise_on_CORS_preflight(request):
    "A simple method for approving CORS preflight request"
    if request.method == 'OPTIONS':
        if request.env.http_access_control_request_method:
             request.response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             request.response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTPOk("single-amendment OPTIONS!", **(request.response.headers))

def _init(request, response):
    response.view = 'generic.json'
    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return OTI(oti=api_utils.get_oti_domain(request))

def _bool_arg(v):
    if isinstance(v, str):
        u = v.upper()
        if u in ['TRUE', 'YES']:
            return True
        if u in ['FALSE', 'NO']:
            return False
    return v

def __extract_json_from_http_call(request, data_field_name='data', **kwargs):
    """Returns the json blob (as a deserialized object) from `kwargs` or the request.body"""
    json_obj = None
    try:
        # check for kwarg data_field_name, or load the full request body
        if data_field_name in kwargs:
            json_obj = kwargs.get(data_field_name, {})
        else:
            json_obj = request.body.read()

        if not isinstance(json_obj, dict):
            json_obj = json.loads(json_obj)
        if data_field_name in json_obj:
            json_obj = json_obj[data_field_name]
    except:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('Exception getting JSON content in __extract_json_from_http_call')
        raise HTTPBadRequest(body=json.dumps({"error": 1, "description": 'no collection JSON found in request'}))
    return json_obj

@view_config(route_name='get_amendment', renderer='json')
def amendment(request):
    """Handle an incoming URL targeting /v3/amendment/{AMENDMENT_ID}
    Use our typical mapping of HTTP verbs to (sort of) CRUD actions.
    """
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')

    def __extract_and_validate_amendment(request, kwargs):
        from pprint import pprint
        try:
            amendment_obj = __extract_json_from_http_call(request, data_field_name='json', **kwargs)
        except HTTPException as err:
            # payload not found
            return None, None, None
        try:
            errors, amendment_adaptor = validate_amendment(amendment_obj)
        except HTTPException as err:
            #_LOG.exception('JSON payload failed validation (raising HTTP response)')
            # pprint(err)
            raise err
        except Exception as err:
            # _LOG.exception('JSON payload failed validation (reporting err.msg)')
            # pprint(err)
            try:
                msg = err.get('msg', 'No message found')
            except:
                msg = str(err)
            raise HTTPBadRequest(body=msg)
        if len(errors) > 0:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            msg = 'JSON payload failed validation with {nerrors} errors:\n{errors}'.format(nerrors=len(errors), errors='\n  '.join(errors))
            # _LOG.exception(msg)
            raise HTTPBadRequest(body=msg)
        return amendment_obj, errors, amendment_adaptor

    # check for an existing amendment ID
    amendment_id = request.matchdict.get('amendment_id', None)
    if amendment_id:
        if not AMENDMENT_ID_PATTERN.match(amendment_id):
            raise HTTPBadRequest(body=json.dumps({"error": 1, "description": "invalid amendment ID ({}) provided".format(amendment_id)}))

    elif request.method != 'POST':
        # N.B. this id is optional when creating a new amendment
        raise HTTPBadRequest(body=json.dumps({"error": 1, "description": 'amendment ID expected after "amendment/"'}))

    # fetch and parse the JSON payload, if any
    amendment_obj, amendment_errors, amendment_adapter = __extract_and_validate_amendment(request,
                                                                                              request.params)
    if (amendment_obj is None) and request.method in ('POST','PUT'):
        raise HTTPBadRequest(body=json.dumps({"error": 1, "description": "amendment JSON expected for HTTP method {}".format(request.method) }))

    if request.method != 'GET':
        # all other methods require authentication
        auth_info = api_utils.authenticate(**request.params)

    # some request types imply git commits; gather any user-provided commit message
    try:
        commit_msg = request.params.get('commit_msg','')
        if commit_msg.strip() == '':
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    if request.params.get('jsoncallback', None) or request.params.get('callback', None):
        # support JSONP requests from another domain
        response.view = 'generic.jsonp'

    if request.method == 'GET':
        # fetch the current amendment JSON
        # _LOG.debug('GET /v2/amendment/{}'.format(str(amendment_id)))
        version_history = None
        comment_html = None
        parent_sha = request.params.get('starting_commit_SHA', None)
        # _LOG.debug('parent_sha = {}'.format(parent_sha))
        # return the correct nexson of study_id, using the specified view
        amendments = api_utils.get_taxonomic_amendment_store(request)
        try:
            r = amendments.return_doc(amendment_id, commit_sha=parent_sha, return_WIP_map=True)
        except:
            # _LOG.exception('GET failed')
            raise HTTPNotFound(json.dumps({"error": 1, "description": "Amendment '{}' GET failure".format(amendment_id)}))
        try:
            amendment_json, head_sha, wip_map = r
            ## if returning_full_study:  # TODO: offer bare vs. full output (w/ history, etc)
            version_history = amendments.get_version_history_for_doc_id(amendment_id)
        except:
            # _LOG.exception('GET failed')
            e = sys.exc_info()[0]
            raise HTTPBadRequest(body=e)
        if not amendment_json:
            raise HTTPNotFound("Amendment '{s}' has no JSON data!".format(s=amendment_id))

        try:
            external_url = amendments.get_public_url(amendment_id)
        except:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            # _LOG.exception('amendment {} not found in external_url'.format(amendment))
            external_url = 'NOT FOUND'
        result = {'sha': head_sha,
                 'data': amendment_json,
                 'branch2sha': wip_map,
                 'external_url': external_url,
                 }
        if version_history:
            result['versionHistory'] = version_history
        return result

    if request.method == 'PUT':
        if not check_not_read_only():
            raise HTTPInternalServerError(body="should raise from check_not_read_only")
        # update an existing amendment with the data provided
        # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.PUT')
        # submit new json for this id, and read the results
        parent_sha = request.params.get('starting_commit_SHA', None)
        merged_sha = None  #TODO: request.params.get('???', None)
        docstore = api_utils.get_taxonomic_amendment_store(request)
        try:
            r = docstore.update_existing_amendment(amendment_id,
                                                   amendment_obj,
                                                   auth_info,
                                                   parent_sha,
                                                   merged_sha,
                                                   commit_msg=commit_msg)
            commit_return = r
        except GitWorkflowError as err:
            raise HTTPBadRequest(body=err.msg)
        except:
            raise HTTPBadRequest(body=traceback.format_exc())

        # check for 'merge needed'?
        mn = commit_return.get('merge_needed')
        if (mn is not None) and (not mn):
            __deferred_push_to_gh_call(request, amendment_id, doc_type='amendment', **request.params)
        return commit_return

    if request.method == 'POST':
        if not check_not_read_only():
            raise HTTPInternalServerError(body="should raise from check_not_read_only")
        # Create a new amendment with the data provided
        # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.POST')
        # submit the json and proposed id (if any), and read the results
        docstore = api_utils.get_taxonomic_amendment_store(request)

        # N.B. add_new_amendment below takes care of minting new ottids,
        # assigning them to new taxa, and returning a per-taxon mapping to the
        # caller. It will assign the new amendment id accordingly!
        try:
            r = docstore.add_new_amendment(amendment_obj,
                                           auth_info,
                                           commit_msg=commit_msg)
            new_amendment_id, commit_return = r
        except GitWorkflowError as err:
            raise HTTPBadRequest(body=err.msg)
        except:
            raise HTTPBadRequest(body=traceback.format_exc())
        if commit_return['error'] != 0:
            # _LOG.debug('add_new_amendment failed with error code')
            raise HTTPBadRequest(body=json.dumps(commit_return))
        __deferred_push_to_gh_call(request, new_amendment_id, doc_type='amendment', **request.params)
        return commit_return

    if request.method == 'DELETE':
        if not check_not_read_only():
            raise HTTPInternalServerError(body="should raise from check_not_read_only")
        # remove this amendment from the docstore
        # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.POST')
        docstore = api_utils.get_taxonomic_amendment_store(request)
        parent_sha = request.params.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTPBadRequest(body='Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        try:
            x = docstore.delete_amendment(amendment_id,
                                          auth_info,
                                          parent_sha,
                                          commit_msg=commit_msg)
            if x.get('error') == 0:
                __deferred_push_to_gh_call(request, None, doc_type='amendment', **request.params)
            return x
        except GitWorkflowError as err:
            raise HTTPBadRequest(body=err.msg)
        except:
            # _LOG.exception('Unknown error in amendment deletion')
            raise HTTPBadRequest(body=traceback.format_exc())
            #raise HTTPBadRequest(body=json.dumps({"error": 1, "description": 'Unknown error in amendment deletion'}))

    raise HTTPInternalServerError(body=T("Unknown HTTP method '{}'".format(request.method)))

