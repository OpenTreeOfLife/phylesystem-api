from pyramid.view import view_config
# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
                                    HTTPException,
                                    HTTPError,
                                    HTTPNotFound, 
                                    HTTPBadRequest,
                                    HTTPInternalServerError,
                                   )
from peyotl.api import OTI
import phylesystem_api.api_utils as api_utils
import json
def _raise400(msg):
    raise HTTPBadRequest(body=json.dumps({"error": 1, "description": msg}))

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

@view_config(route_name='study_properties', renderer='json')
def properties(request):
    oti = _init(request, request.response)
    n = list(oti.node_search_term_set)
    n.sort()
    t = list(oti.tree_search_term_set)
    t.sort()
    s = list(oti.study_search_term_set)
    s.sort()
    return {'node_properties': n,
            'tree_properties': t,
            'study_properties': s}


@view_config(route_name='find_studies', renderer='json')
def find_studies(request):
    # if behavior varies based on /v1/, /v2/, ...
    api_version = request.matchdict['api_version']
    oti = _init(request, request.response)
    verbose = _bool_arg(request.params.get('verbose', False))
    if (verbose is not True) and (verbose is not False):
        _raise400('"verbose" setting must be a boolean')
    field = request.params.get('property')
    try:
        if field is None:
            resp = oti.find_all_studies(verbose=verbose)
        else:
            value = request.params.get('value')
            if value is None:
                _raise400('If "property" is sent, a "value" argument must be used.')
            exact = _bool_arg(request.params.get('exact', False))
            if (exact is not True) and (exact is not False):
                _raise400('"exact" setting must be a boolean')
            try:
                resp = oti.find_studies({field: value}, verbose=verbose, exact=exact)
            except ValueError as x:
                _raise400(x.message)
    except HTTPException:
        raise
    except HTTPError:
        raise
    except Exception as x:
        msg = ",".join(x.args)
        raise HTTPInternalServerError(
                body=json.dumps({"error": 1, 
                                 "description": "Unexpected error calling oti: {}".format(msg)}))
    return resp


@view_config(route_name='find_trees', renderer='json')
def find_trees(request):
    # if behavior varies based on /v1/, /v2/, ...
    api_version = request.matchdict['api_version']
    #import pdb; pdb.set_trace()
    try:
        msg = request.json_body
    except:
        _raise400('missing or invalid request JSON')
    oti = _init(request, request.response)
    verbose = _bool_arg(msg.get('verbose', False))
    if (verbose is not True) and (verbose is not False):
        _raise400('"verbose" setting must be a boolean')
    field = msg.get('property')
    if field is None:
        _raise400('A "property" argument must be used.')
    value = msg.get('value')
    if value is None:
        _raise400('A "value" argument must be used.')
    exact = _bool_arg(msg.get('exact', False))
    if (exact is not True) and (exact is not False):
        _raise400('"exact" setting must be a boolean')
    try:
        resp = oti.find_trees({field: value}, verbose=verbose, exact=exact)
    except HTTPException:
        raise
    except ValueError as x:
        _raise400(x.message)
    except Exception as x:
        msg = ",".join(x.args)
        raise HTTPInternalServerError(
                body=json.dumps({"error": 1, 
                                 "description": "Unexpected error calling oti: {}".format(msg)}))
    return resp
