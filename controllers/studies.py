#!/usr/bin/env python
from peyotl.api import OTI, APIDomains
import api_utils
import json
def _raise400(msg):
    raise HTTP(400, json.dumps({"error": 1, "description": msg}))

def _init(request, response):
    response.view = 'generic.json'
    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return OTI(oti=api_utils.get_oti_domain(request))
def _bool_arg(v):
    if isinstance(v, str) or isinstance(v, unicode):
        u = v.upper()
        if u in ['TRUE', 'YES']:
            return True
        if u in ['FALSE', 'NO']:
            return False
    return v

def properties():
    oti = _init(request, response)
    n = list(oti.node_search_term_set)
    n.sort()
    t = list(oti.tree_search_term_set)
    t.sort()
    s = list(oti.study_search_term_set)
    s.sort()
    return json.dumps({'node_properties': n,
                       'tree_properties': t,
                       'study_properties': s})

def find_studies():
    oti = _init(request, response)
    verbose = _bool_arg(request.vars.get('verbose', False))
    if (verbose is not True) and (verbose is not False):
        _raise400('"verbose" setting must be a boolean')
    field = request.vars.get('property')
    if field is None:
        resp = oti.find_all_studies(verbose=verbose)
    else:
        value = request.vars.get('value')
        if value is None:
            _raise400('If "property" is sent, a "value" argument must be used.')
        exact = _bool_arg(request.vars.get('exact', False))
        if (exact is not True) and (exact is not False):
            _raise400('"exact" setting must be a boolean')
        resp = oti.find_studies({field: value}, verbose=verbose, exact=exact)
    return json.dumps(resp)
