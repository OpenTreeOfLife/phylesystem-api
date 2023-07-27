import json
import logging
import os

import phylesystem_api.api_utils as api_utils
from peyotl.nexson_syntax import read_as_json

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
    HTTPException,
    HTTPInternalServerError,
)
from pyramid.view import view_config

_LOG = logging.getLogger("phylesystem_api")


def _bool_arg(v):
    if isinstance(v, str):
        u = v.upper()
        if u in ["TRUE", "YES"]:
            return True
        if u in ["FALSE", "NO"]:
            return False
    return v


"""
    raise HTTPBadRequest(body=json.dumps({"error": 1, "description": msg}))
"""


@view_config(route_name="list_all_amendment_ids", renderer="json")
def list_all_amendment_ids(request):
    docstore = api_utils.get_taxonomic_amendment_store(request)
    return docstore.get_amendment_ids()


@view_config(route_name="list_all_amendments", renderer="json")
def list_all(request):
    api_utils.raise_on_CORS_preflight(request)
    # TODO: proxy to oti for a filtered list?
    # For now, let's just return all collections (complete JSON)
    amendment_list = []
    try:
        docstore = api_utils.get_taxonomic_amendment_store(request)
        # Convert these to more closely resemble the output of find_all_studies
        for id, props in docstore.iter_doc_objs():
            # reckon and add 'lastModified' property, based on commit history?
            latest_commit = docstore.get_version_history_for_doc_id(id)[0]
            props.update(
                {
                    "id": id,
                    "lastModified": {
                        "author_name": latest_commit.get("author_name"),
                        "relative_date": latest_commit.get("relative_date"),
                        "display_date": latest_commit.get("date"),
                        "ISO_date": latest_commit.get("date_ISO_8601"),
                        "sha": latest_commit.get("id"),  # this is the commit hash
                    },
                }
            )
            amendment_list.append(props)
    except HTTPException:
        raise
    except Exception as x:
        msg = ",".join(x.args)
        raise HTTPInternalServerError(
            body=json.dumps(
                {
                    "error": 1,
                    "description": "Unexpected error calling oti: {}".format(msg),
                }
            )
        )
    return amendment_list


@view_config(route_name="get_amendments_config", renderer="json")
def get_amendments_config(request):
    _LOG.debug("get_amendments_config")
    api_utils.raise_on_CORS_preflight(request)
    docstore = api_utils.get_taxonomic_amendment_store(request)
    return docstore.get_configuration_dict()


@view_config(route_name="amendments_push_failure", renderer="json")
def amendments_push_failure(request):
    api_utils.raise_on_CORS_preflight(request)
    # this should find a type-specific push_failure file
    request.matchdict["doc_type"] = "amendment"
    fail_file = api_utils.get_failed_push_filepath(request)
    if os.path.exists(fail_file):
        try:
            blob = read_as_json(fail_file)
        except:
            blob = {"message": "could not read push fail file"}
        blob["pushes_succeeding"] = False
    else:
        blob = {"pushes_succeeding": True}
    blob["doc_type"] = request.matchdict.get("doc_type", "nexson")
    return blob
