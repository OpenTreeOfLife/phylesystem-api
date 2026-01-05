import os
import logging
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
    all_collections_list,
)

_LOG = logging.getLogger("phylesystem_api")
_LOG.debug("start collections")


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
    try:
        return all_collections_list(request)
    except HTTPException:
        raise
    except:
        _LOG.exception("top level find_collections... converting to http err...")
        raise_int_server_err("Unexpected error gathering collections")
