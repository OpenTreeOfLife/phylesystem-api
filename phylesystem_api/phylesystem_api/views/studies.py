from pyramid.view import view_config
# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
                                    HTTPException,
                                    HTTPError,
                                    HTTPConflict,
                                    HTTPNotFound, 
                                    HTTPBadRequest,
                                    HTTPInternalServerError,
                                   )
from peyotl.api import OTI
import phylesystem_api.api_utils as api_utils
from phylesystem_api.api_utils import find_in_request
from peyotl.phylesystem.git_workflows import GitWorkflowError, \
                                             merge_from_master
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
    verbose = _bool_arg(find_in_request(request, 'verbose', False))
    if (verbose is not True) and (verbose is not False):
        _raise400('"verbose" setting must be a boolean')
    field = find_in_request(request, 'property', None)
    try:
        if field is None:
            match_list = oti.find_all_studies(verbose=verbose)
            resp = {'matched_studies': match_list}
        else:
            value = find_in_request(request, 'value', None)
            if value is None:
                _raise400('If "property" is sent, a "value" argument must be used.')
            exact = _bool_arg(find_in_request(request, 'exact', False))
            if (exact is not True) and (exact is not False):
                _raise400('"exact" setting must be a boolean')
            try:
                match_list = oti.find_studies({field: value}, verbose=verbose, exact=exact)
                resp = {'matched_studies': match_list}
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
        match_list = oti.find_trees({field: value}, verbose=verbose, exact=exact)
        resp = {'matched_studies': match_list}
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


@view_config(route_name='merge_study_changes', renderer='json')
def merge_study_changes(request):
    """OpenTree API methods relating to updating branches

    curl -X PUT https://devapi.opentreeoflife.org/v3/studies/merge?study_id=9&starting_commit_SHA=152316261261342&auth_token=$GITHUB_OAUTH_TOKEN

    If the request is successful, a JSON response similar to this will be returned:

    {
        "error": 0,
        "branch_name": "my_user_9_2",
        "description": "Updated branch",
        "sha": "dcab222749c9185797645378d0bda08d598f81e7",
        "merged_SHA": "16463623459987070600ab2757540c06ddepa608",
    }

    'merged_SHA' must be included in the next PUT for this study (unless you are
        happy with your work languishing on a WIP branch instead of master).

    If there is an error, an HTTP 400 error will be returned with a JSON response similar
    to this:

    {
        "error": 1,
        "description": "Could not merge master into WIP! Details: ..."
    }
    """
    # if behavior varies based on /v1/, /v2/, ...
    api_version = request.matchdict['api_version']
    resource_id = request.matchdict['study_id']
    starting_commit_SHA = request.matchdict['starting_commit_SHA']

    api_utils.raise_if_read_only()

    # this method requires authentication
    auth_info = api_utils.authenticate(**request.json_body)

    phylesystem = api_utils.get_phylesystem(request)
    gd = phylesystem.create_git_action(resource_id)
    try:
        return merge_from_master(gd, resource_id, auth_info, starting_commit_SHA)
    except GitWorkflowError as err:
        raise HTTPBadRequest(body=json.dumps({"error": 1, "description": err.msg}))
    except:
        import traceback
        m = traceback.format_exc()
        raise HTTPConflict(detail=json.dumps({
            "error": 1,
            "description": "Could not merge! Details: %s" % (m)
        }))

    #import pdb; pdb.set_trace()
    return locals()
