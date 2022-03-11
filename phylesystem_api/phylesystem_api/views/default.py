from pyramid.view import (
                          view_config,
                          notfound_view_config,
                         )
from pyramid.response import Response
import requests
from peyotl import concatenate_collections, \
                   tree_is_in_collection

from peyotl.phylesystem.git_workflows import GitWorkflowError, \
                                             validate_and_convert_nexson
import phylesystem_api.api_utils as api_utils
try:
    import anyjson
except:
    import json
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads

_GLOG = api_utils.get_logger(None, 'ot_api.default.global')
try:
    from open_tree_tasks import call_http_json
    #_GLOG.debug('call_http_json imported')
except:
    call_http_json = None
    _GLOG.debug('call_http_json was not imported from open_tree_tasks')

@view_config(route_name='index', renderer='phylesystem_api:templates/home.jinja2')
def home_view(request):
    # a simple README web page for the curious
    return {'title': 'phylesystem API'}

@view_config(route_name='api_root', renderer='json',
             request_method='POST')
@view_config(route_name='api_version_root', renderer='json')
@view_config(route_name='api_version_noslash', renderer='json')
@view_config(route_name='studies_root', renderer='json')
@view_config(route_name='amendments_root', renderer='json')
@view_config(route_name='collections_root', renderer='json')
def base_API_view(request):
    # a tiny JSON description of the API and where to find documentation
    api_version = request.matchdict['api_version']
    # TODO: Modify URLs if they differ across API versions
    return {
        "description": "The Open Tree API {}".format(api_version),
        "documentation_url": "https://github.com/OpenTreeOfLife/phylesystem-api/tree/master/docs",
        "source_url": "https://github.com/OpenTreeOfLife/phylesystem-api"
    }

# all other pages should be JSON, so here's a suitable 404 response
@notfound_view_config(renderer='json',
                      accept='application/json',
                      append_slash=True)
def notfound(request):
    return Response(
        body=anyjson.dumps({'message': 'Nothing found at this URL'}),
        status='404 Not Found',
        charset='UTF-8',
        content_type='application/json')

@view_config(route_name='render_markdown')
def render_markdown(request):
    # Convert POSTed Markdown to HTML (e.g., for previews in web UI)
    src = request.body.decode('utf-8')
    html = api_utils.markdown_to_html( src, open_links_in_new_window=True )
    return Response(body=html, content_type='text/html')

@view_config(route_name='phylesystem_config', renderer='json')
def phylesystem_config(request):
    # general information about the hosted phylesystem
    phylesystem = api_utils.get_phylesystem(request)
    return phylesystem.get_configuration_dict()

@view_config(route_name='raw_study_list', renderer='json')
def study_list(request):
    phylesystem = api_utils.get_phylesystem(request)
    studies = phylesystem.get_study_ids()
    return anyjson.dumps(studies)

@view_config(route_name='trees_in_synth', renderer='json')
def trees_in_synth(request):
    """Return an "artificial" collection that contains all trees (and
    contributors) from all of the tree collections that contribute to
    synthesis.
    """
    coll_id_list = _get_synth_input_collection_ids()
    coll_list = []
    cds = api_utils.get_tree_collection_store(request)
    for coll_id in coll_id_list:
        try:
            coll_list.append(cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0])
        except:
            msg = 'GET of collection {} failed'.format(coll_id)
            # _LOG.exception(msg)
            raise HTTP(404, anyjson.dumps({"error": 1, "description": msg}))
    try:
        result = concatenate_collections(coll_list)
    except:
        # _LOG.exception('concatenation of collections failed')
        e = sys.exc_info()[0]
        _raise_HTTP_from_msg(e)
    return anyjson.dumps(result)

@view_config(route_name='include_tree_in_synth', renderer='json')
def include_tree_in_synth(request):
    study_id = kwargs.get('study_id', "").strip()
    tree_id = kwargs.get('tree_id', "").strip()
    # check for empty/missing ids
    if (study_id == '') or (tree_id == ''):
        raise HTTP(400, '{"error": 1, "description": "Expecting study_id and tree_id arguments"}')
    # examine this study and tree, to confirm it exists *and* to capture its name
    sds = api_utils.get_phylesystem(request)
    found_study = None
    try:
        found_study = sds.return_doc(study_id, commit_sha=None, return_WIP_map=False)[0]
        tree_collections_by_id = found_study.get('nexml').get('treesById')
        for trees_id, trees_collection in list(tree_collections_by_id.items()):
            trees_by_id = trees_collection.get('treeById')
            if tree_id in list(trees_by_id.keys()):
                # _LOG.exception('*** FOUND IT ***')
                found_tree = trees_by_id.get(tree_id)
        found_tree_name = found_tree['@label'] or tree_id
        #_LOG.exception('*** FOUND IT: {}'.format(found_tree_name))
    except:  # report a missing/misidentified tree
        # _LOG.exception('problem finding tree')
        raise HTTP(404, '{{"error": 1, "description": "Specified tree \'{t}\' in study \'{s}\' not found! Save this study and try again?"}}'.format(s=study_id,t=tree_id))
    already_included_in_synth_input_collections = False
    # Look ahead to see if it's already in an included collection; if so, skip
    # adding it again.
    coll_id_list = _get_synth_input_collection_ids()
    cds = api_utils.get_tree_collection_store(request)
    for coll_id in coll_id_list:
        try:
            coll = cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0]
        except:
            msg = 'GET of collection {} failed'.format(coll_id)
            # _LOG.exception(msg)
            raise HTTP(404, anyjson.dumps({"error": 1, "description": msg}))
        if tree_is_in_collection(coll, study_id, tree_id):
            already_included_in_synth_input_collections = True
    if not already_included_in_synth_input_collections:
        # find the default synth-input collection and parse its JSON
        default_collection_id = coll_id_list[-1]
        # N.B. For now, we assume that the last listed synth-input collection
        # is the sensible default, so we already have it in coll
        decision_list = coll.get('decisions', [])
        # construct and add a sensible decision entry for this tree
        decision_list.append({
            'name': found_tree_name or "",
            'treeID': tree_id,
            'studyID': study_id,
            'SHA': "",
            'decision': "INCLUDED",
            'comments': "Added via API (include_tree_in_synth) from {p}".format(p=found_study.get('nexml')['^ot:studyPublicationReference'])
            })
        # update (or add) the decision list for this collection
        coll['decisions'] = decision_list
        # update the default collection (forces re-indexing)
        try:
            auth_info = api_utils.authenticate(**kwargs)
            owner_id = auth_info.get('login', None)
        except:
            msg = 'include_tree_in_synth(): Authentication failed'
            raise HTTP(404, anyjson.dumps({"error": 1, "description": msg}))
        try:
            parent_sha = kwargs.get('starting_commit_SHA', None)
            merged_sha = None  #TODO: kwargs.get('???', None)
        except:
            msg = 'include_tree_in_synth(): fetch of starting_commit_SHA failed'
            raise HTTP(404, anyjson.dumps({"error": 1, "description": msg}))
        try:
            r = cds.update_existing_collection(owner_id,
                                               default_collection_id,
                                               coll,
                                               auth_info,
                                               parent_sha,
                                               merged_sha,
                                               commit_msg="Updated via API (include_tree_in_synth)")
            commit_return = r
        except GitWorkflowError as err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())

        # check for 'merge needed'?
        mn = commit_return.get('merge_needed')
        if (mn is not None) and (not mn):
            api_utils.deferred_push_to_gh_call(request, default_collection_id, doc_type='collection', **kwargs)

    # fetch and return the updated list of synth-input trees
    return trees_in_synth(kwargs)

@view_config(route_name='exclude_tree_from_synth', renderer='json')
def exclude_tree_from_synth(request):
    study_id = kwargs.get('study_id', "").strip()
    tree_id = kwargs.get('tree_id', "").strip()
    # check for empty/missing ids
    if (study_id == '') or (tree_id == ''):
        raise HTTP(400, '{"error": 1, "description": "Expecting study_id and tree_id arguments"}')
    # find this tree in ANY synth-input collection; if found, remove it and update the collection
    coll_id_list = _get_synth_input_collection_ids()
    cds = api_utils.get_tree_collection_store(request)
    try:
        auth_info = api_utils.authenticate(**kwargs)
        owner_id = auth_info.get('login', None)
    except:
        msg = 'include_tree_in_synth(): Authentication failed'
        raise HTTP(404, anyjson.dumps({"error": 1, "description": msg}))
    for coll_id in coll_id_list:
        try:
            coll = cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0]
        except:
            msg = 'GET of collection {} failed'.format(coll_id)
            raise HTTP(404, anyjson.dumps({"error": 1, "description": msg}))
        if tree_is_in_collection(coll, study_id, tree_id):
            # remove it and update the collection
            decision_list = coll.get('decisions', [])
            coll['decisions'] = [d for d in decision_list if not ((d['studyID'] == study_id) and (d['treeID'] == tree_id))]
            # N.B. that _both_ ids (for study and tree) must match to remove a decision!
            # update the collection (forces re-indexing)
            parent_sha = kwargs.get('starting_commit_SHA', None)
            merged_sha = None  #TODO: kwargs.get('???', None)
            try:
                r = cds.update_existing_collection(owner_id,
                                                   coll_id,
                                                   coll,
                                                   auth_info,
                                                   parent_sha,
                                                   merged_sha,
                                                   commit_msg="Updated via API (include_tree_in_synth)")
                commit_return = r
            except GitWorkflowError as err:
                _raise_HTTP_from_msg(err.msg)
            except:
                raise HTTP(400, traceback.format_exc())

            # check for 'merge needed'?
            mn = commit_return.get('merge_needed')
            if (mn is not None) and (not mn):
                api_utils.deferred_push_to_gh_call(request, coll_id, doc_type='collection', **kwargs)

    # fetch and return the updated list of synth-input trees
    return trees_in_synth(kwargs)



def _get_synth_input_collection_ids():
    """Return a list of all collection ids for the collections that contribute
    to synthesis (based on the current propinquity configuration).
    """
    # URL could be configurable, but I'm not sure we've ever changed this...
    url_of_synth_config = 'https://raw.githubusercontent.com/mtholder/propinquity/master/config.opentree.synth'
    try:
        resp = requests.get(url_of_synth_config)
        conf_fo = StringIO(resp.content)
    except:
        raise HTTP(504, 'Could not fetch synthesis list from {}'.format(url_of_synth_config))
    cfg = SafeConfigParser()
    try:
        cfg.readfp(conf_fo)
    except:
        raise HTTP(500, 'Could not parse file from {}'.format(url_of_synth_config))
    try:
        coll_id_list = cfg.get('synthesis', 'collections').split()
    except:
        raise HTTP(500, 'Could not find a collection list in file from {}'.format(url_of_synth_config))
    return coll_id_list

def _raise_HTTP_from_msg(msg):
    raise HTTP(400, anyjson.dumps({"error": 1, "description": msg}))

def check_not_read_only():
    if api_utils.READ_ONLY_MODE:
        raise HTTP(403, anyjson.dumps({"error": 1, "description": "phylesystem-api running in read-only mode"}))
    return True

