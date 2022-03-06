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

from peyotl.collections_store import OWNER_ID_PATTERN, \
                                     COLLECTION_ID_PATTERN
from peyotl.collections_store.validation import validate_collection

def __extract_and_validate_collection(request, kwargs):
    from pprint import pprint
    try:
        collection_obj = __extract_json_from_http_call(request, data_field_name='json', **kwargs)
    except HTTPException as err:
        # payload not found
        return None, None, None
    try:
        errors, collection_adaptor = validate_collection(collection_obj)
    except HTTPException as err:
        # _LOG.exception('JSON payload failed validation (raising HTTP response)')
        pprint(err)
        raise err
    except Exception as err:
        # _LOG.exception('JSON payload failed validation (reporting err.msg)')
        pprint(err)
        try:
            msg = err.get('msg', 'No message found')
        except:
            msg = str(err)
        raise HTTPBadRequest(msg)
    if len(errors) > 0:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        msg = 'JSON payload failed validation with {nerrors} errors:\n{errors}'.format(nerrors=len(errors), errors='\n  '.join(errors))
        # _LOG.exception(msg)
        raise HTTPBadRequest(msg)
    return collection_obj, errors, collection_adaptor

@view_config(route_name='collection_CORS_preflight', renderer='json')
@view_config(route_name='create_collection', renderer='json', request_method='OPTIONS')
def collection_CORS_preflight(request):
    api_utils.raise_on_CORS_preflight(request)

@view_config(route_name='create_collection', renderer='json', request_method='POST')
def create_collection(request):
    # gather any user-provided git-commit message
    try:
        commit_msg = request.params.get('commit_msg','')
        if commit_msg.strip() == '':
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    api_utils.raise_if_read_only()

    # fetch and parse the JSON payload, if any 
    collection_obj, collection_errors, collection_adapter = __extract_and_validate_collection(request, kwargs)
    if (amendment_obj is None):
        raise HTTPBadRequest(body=json.dumps({"error": 1, "description": "collection JSON expected for HTTP method {}".format(request.method) }))

    auth_info = None
    if owner_id is None:
        # set this explicitly to the logged-in userid (make sure the user is allowed!)
        auth_info = api_utils.authenticate(**request.params)
        owner_id = auth_info.get('login', None)
        if owner_id is None:
            raise HTTPBadRequest(json.dumps({"error": 1, "description": "no GitHub userid found for HTTP method {}".format(request.env.request_method) }))
    if collection_id is None:
        # try to extract a usable collection ID from the JSON payload (confirm owner_id against above)
        url = collection_obj.get('url', None)
        if url is None:
            raise HTTPBadRequest(json.dumps({"error": 1, "description": "no collection URL provided in query string or JSON payload"}))
        try:
            collection_id = url.split('/collection/')[1]
        except:
            # _LOG.exception('{} failed'.format(request.env.request_method))
            raise HTTPNotFound(json.dumps({"error": 1, "description": "invalid URL, no collection id found: {}".format(url)}))
        try:
            assert collection_id.split('/')[0] == owner_id
        except:
            # _LOG.exception('{} failed'.format(request.env.request_method))
            raise HTTP(404, json.dumps({"error": 1, "description": "collection URL in JSON doesn't match logged-in user: {}".format(url)}))

    # Create a new collection with the data provided
    auth_info = auth_info or api_utils.authenticate(**request.params)
    # submit the json and proposed id (if any), and read the results
    docstore = api_utils.get_tree_collection_store(request)
    try:
        r = docstore.add_new_collection(owner_id, 
                                        collection_obj, 
                                        auth_info,
                                        collection_id, 
                                        commit_msg=commit_msg)
        new_collection_id, commit_return = r
    except GitWorkflowError as err:
        raise HTTPBadRequest(anyjson.dumps({"error": 1, "description": msg}))
    except:
        raise HTTPBadRequest(traceback.format_exc())
    if commit_return['error'] != 0:
        # _LOG.debug('add_new_collection failed with error code')
        raise HTTPBadRequest(json.dumps(commit_return))
    api_utils.deferred_push_to_gh_call(request, new_collection_id, doc_type='collection', **kwargs)
    return commit_return

@view_config(route_name='create_collection', renderer='json', request_method='POST')
def create_collection(request):
    pass
"""
fetch_collection
update_collection
delete_collection
"""
