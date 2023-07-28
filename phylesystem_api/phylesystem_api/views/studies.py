import json
import threading

import phylesystem_api.api_utils as api_utils
from phylesystem_api.api_utils import find_in_request, raise400, bool_arg

# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import HTTPException, HTTPBadRequest
from pyramid.view import view_config


def _configure_response(response):
    response.view = "generic.json"
    # CORS support for cross-domain API requests (from anywhere)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"


@view_config(route_name="study_properties", renderer="json")
def properties(request):
    _configure_response(request.response)
    return _get_study_properties(request)


# global dict so that we don't have to fetch the same info from otindex repeatedly
_study_prop_dict = None
_study_prop_dict_lock = threading.Lock()


def _get_study_properties(request):
    global _study_prop_dict
    if _study_prop_dict is None:
        with _study_prop_dict_lock:
            if _study_prop_dict is not None:
                return _study_prop_dict

            oti = api_utils.get_oti_wrapper(request)
            n = list(oti.node_search_term_set)
            n.sort()
            t = list(oti.tree_search_term_set)
            t.sort()
            s = list(oti.study_search_term_set)
            s.sort()
            _study_prop_dict = {
                "node_properties": n,
                "tree_properties": t,
                "study_properties": s,
            }
    return _study_prop_dict


def validate_bool_setting(request, prop_name, default):
    bs = bool_arg(find_in_request(request, prop_name, default))
    if (bs is not True) and (bs is not False):
        raise400('"{}" setting must be a boolean'.format(prop_name))
    return bs


@view_config(route_name="find_studies", renderer="json")
def find_studies(request):
    oti = api_utils.get_oti_wrapper(request)
    verbose = validate_bool_setting(request, "verbose", False)
    field = find_in_request(request, "property", None)
    try:
        if field is None:
            match_list = oti.find_all_studies(verbose=verbose)
        else:
            value = find_in_request(request, "value", None)
            if value is None:
                raise400('If "property" is sent, a "value" argument must be used.')
            exact = validate_bool_setting(request, "exact", False)
            try:
                match_list = oti.find_studies(
                    {field: value}, verbose=verbose, exact=exact
                )
            except ValueError as x:
                raise400(str(x))
    except HTTPException:
        raise
    except Exception as x:
        msg = "Unexpected error calling oti: {}".format(",".join(x.args))
        api_utils.raise_int_server_err(msg)
    _configure_response(request.response)
    return {"matched_studies": match_list}


@view_config(route_name="find_trees", renderer="json")
def find_trees(request):
    try:
        msg = request.json_body
    except:
        raise400("missing or invalid request JSON")
    _configure_response(request.response)
    oti = api_utils.get_oti_wrapper(request)
    verbose = validate_bool_setting(request, "verbose", False)
    field = msg.get("property")
    if field is None:
        raise400('A "property" argument must be used.')
    value = msg.get("value")
    if value is None:
        raise400('A "value" argument must be used.')
    exact = validate_bool_setting(request, "exact", False)
    try:
        match_list = oti.find_trees({field: value}, verbose=verbose, exact=exact)
    except HTTPException:
        raise
    except ValueError as x:
        raise400(str(x))
    except Exception as x:
        msg = "Unexpected error calling oti: {}".format(",".join(x.args))
        api_utils.raise_int_server_err(msg)
    return {"matched_studies": match_list}
