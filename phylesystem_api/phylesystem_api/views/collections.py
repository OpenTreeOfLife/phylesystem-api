import os

from peyotl.nexson_syntax import read_as_json

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
    HTTPException,
    HTTPNotImplemented,
)
from pyramid.view import view_config

from phylesystem_api.api_utils import (
    get_last_modified_dict,
    get_tree_collection_store,
    raise_on_CORS_preflight,
    raise_int_server_err,
)


@view_config(route_name="list_all_collection_ids", renderer="json")
def list_all_collection_ids(request):
    docstore = get_tree_collection_store(request)
    return docstore.get_collection_ids()


@view_config(route_name="collection_properties", renderer="json")
def collection_properties(request):
    raise_on_CORS_preflight(request)
    raise HTTPNotImplemented(
        "Now we'd list all searchable properties in tree collections!"
    )


@view_config(route_name="find_trees_in_collections", renderer="json")
def find_trees_in_collections(request):
    raise_on_CORS_preflight(request)
    raise HTTPNotImplemented(
        "Now we'd list all collections holding trees that match the criteria provided!"
    )


@view_config(route_name="find_collections", renderer="json")
def find_collections(request):
    raise_on_CORS_preflight(request)
    # TODO: proxy to oti for a filtered list?
    # For now, let's just return all collections (complete JSON)
    docstore = get_tree_collection_store(request)
    # Convert these to more closely resemble the output of find_all_studies
    collection_list = []
    try:
        for c_id, props in docstore.iter_doc_objs():
            props["id"] = c_id
            props["lastModified"] = get_last_modified_dict(docstore, c_id)
            collection_list.append(props)
    except HTTPException:
        raise
    except:
        raise_int_server_err("Unexpected error gathering collections")
    return collection_list
