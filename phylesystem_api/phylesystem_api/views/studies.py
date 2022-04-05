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
import traceback
import datetime
import codecs
import os

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
    auth_info = api_utils.authenticate(request)

    phylesystem = api_utils.get_phylesystem(request)
    gd = phylesystem.create_git_action(resource_id)
    try:
        return merge_from_master(gd, resource_id, auth_info, starting_commit_SHA)
    except GitWorkflowError as err:
        raise HTTPBadRequest(body=json.dumps({"error": 1, "description": err.msg}))
    except:
        m = traceback.format_exc()
        raise HTTPConflict(detail=json.dumps({
            "error": 1,
            "description": "Could not merge! Details: %s" % (m)
        }))

    #import pdb; pdb.set_trace()
    return locals()

@view_config(route_name='push_study_changes', renderer='json')
def push_study_changes(request):
    """OpenTree API method to update branch on master

    ASSUMES 'doc_type' is 'nexson' (vs. 'collection', 'favorites', ...)

    curl -X POST http://localhost:8000/v3/push/9
    curl -X POST http://localhost:8000/v3/push/
    """
    # if behavior varies based on /v1/, /v2/, ...
    api_version = request.matchdict['api_version']
    doc_type='nexson'
    resource_id = request.matchdict['study_id']

    api_utils.raise_if_read_only()

    _LOG = api_utils.get_logger(request, 'ot_api.push.v3.PUT')
    fail_file = api_utils.get_failed_push_filepath(request, doc_type=doc_type)
    _LOG.debug(">> fail_file for type '{t}': {f}".format(t=doc_type, f=fail_file))

    # this method requires authentication
    auth_info = api_utils.authenticate(request)

    phylesystem = api_utils.get_phylesystem(request)
    try:
        phylesystem.push_study_to_remote('GitHubRemote', resource_id)
    except:
        m = traceback.format_exc()
        _LOG.warn('Push of study {s} failed. Details: {m}'.format(s=resource_id, m=m))
        if os.path.exists(fail_file):
            _LOG.warn('push failure file "{f}" already exists. This event not logged there'.format(f=fail_file))
        else:
            timestamp = datetime.datetime.utcnow().isoformat()
            try:
                ga = phylesystem.create_git_action(resource_id)
            except:
                m = 'Could not create an adaptor for git actions on study ID "{}". ' \
                    'If you are confident that this is a valid study ID, please report this as a bug.'
                m = m.format(resource_id)
                raise HTTPBadRequest(body=json.dumps({'error': 1, 'description': m}))
            master_sha = ga.get_master_sha()
            obj = {'date': timestamp,
                   'study': resource_id,
                   'commit': master_sha,
                   'stacktrace': m}
            api_utils.atomic_write_json_if_not_found(obj, fail_file, request)
            _LOG.warn('push failure file "{f}" created.'.format(f=fail_file))
        raise HTTPConflict(json.dumps({
            "error": 1,
            "description": "Could not push! Details: {m}".format(m=m)
        }))

    return {'error': 0,
            'description': 'Push succeeded'}
