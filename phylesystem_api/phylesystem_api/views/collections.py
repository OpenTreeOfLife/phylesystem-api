from pyramid.view import view_config
# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
                                    HTTPException,
                                    HTTPError,
                                    HTTPNotFound,
                                    HTTPBadRequest,
                                    HTTPInternalServerError,
                                    HTTPNotImplemented,
                                   )
from peyotl.api import OTI
import phylesystem_api.api_utils as api_utils
import json

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

@view_config(route_name='get_collections_config', renderer='json')
def get_collections_config(request):
    api_utils.raise_on_CORS_preflight(request)
    docstore = api_utils.get_tree_collection_store(request)
    return docstore.get_configuration_dict()

@view_config(route_name='collections_push_failure', renderer='json')
def collections_push_failure(request):
    # this should find a type-specific PUSH_FAILURE file
    api_utils.raise_on_CORS_preflight(request)
    request.matchdict['doc_type'] = 'collection'
    return push_failure()

@view_config(route_name='list_all_collection_ids', renderer='json')
def list_all_collection_ids(request):
    docstore = api_utils.get_tree_collection_store(request)
    return docstore.get_collection_ids()

@view_config(route_name='collection_properties', renderer='json')
def collection_properties(request):
    api_utils.raise_on_CORS_preflight(request)
    raise HTTPNotImplemented("Now we'd list all searchable properties in tree collections!")

@view_config(route_name='find_trees_in_collections', renderer='json')
def find_trees_in_collections(request):
    api_utils.raise_on_CORS_preflight(request)
    raise HTTPNotImplemented("Now we'd list all collections holding trees that match the criteria provided!")

@view_config(route_name='find_collections', renderer='json')
def find_collections(request):
    api_utils.raise_on_CORS_preflight(request)
    # if behavior varies based on /v1/, /v2/, ...
    api_version = request.matchdict['api_version']
    # TODO: proxy to oti for a filtered list?
    # For now, let's just return all collections (complete JSON)
    try:
        docstore = api_utils.get_tree_collection_store(request)
        # Convert these to more closely resemble the output of find_all_studies
        collection_list = []
        for id, props in docstore.iter_doc_objs():
            # reckon and add 'lastModified' property, based on commit history?
            latest_commit = docstore.get_version_history_for_doc_id(id)[0]
            props.update({
                'id': id,
                'lastModified': {
                        'author_name': latest_commit.get('author_name'),
                        'relative_date': latest_commit.get('relative_date'),
                        'display_date': latest_commit.get('date'),
                        'ISO_date': latest_commit.get('date_ISO_8601'),
                        'sha': latest_commit.get('id')  # this is the commit hash
                        }
                })
            collection_list.append(props)
    except HTTPException:
        raise
    except HTTPError:
        raise
    except Exception as x:
        msg = ",".join(x.args)
        raise HTTPInternalServerError(
                body=json.dumps({"error": 1,
                                 "description": "Unexpected error calling oti: {}".format(msg)}))
    return json.dumps(collection_list)
