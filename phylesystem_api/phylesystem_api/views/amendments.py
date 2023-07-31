import logging

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
    HTTPException,
)
from pyramid.view import view_config

from phylesystem_api.api_utils import (
    get_taxonomic_amendment_store,
    raise_on_CORS_preflight,
    raise_int_server_err,
    get_last_modified_dict,
)

_LOG = logging.getLogger("phylesystem_api")


@view_config(route_name="list_all_amendment_ids", renderer="json")
def list_all_amendment_ids(request):
    docstore = get_taxonomic_amendment_store(request)
    return docstore.get_amendment_ids()


@view_config(route_name="list_all_amendments", renderer="json")
def list_all(request):
    raise_on_CORS_preflight(request)
    # TODO: proxy to oti for a filtered list?
    # For now, let's just return all collections (complete JSON)
    amendment_list = []
    try:
        docstore = get_taxonomic_amendment_store(request)
        # Convert these to more closely resemble the output of find_all_studies
        for a_id, props in docstore.iter_doc_objs():
            props["id"] = a_id
            props["lastModified"] = get_last_modified_dict(docstore, a_id)
            amendment_list.append(props)
    except HTTPException:
        raise
    except Exception as x:
        msg = "Unexpected error calling oti: {}".format(",".join(x.args))
        raise_int_server_err(msg)
    return amendment_list
