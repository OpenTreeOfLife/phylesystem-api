import requests
import urllib2
import os, sys

import json
try:
    import anyjson
except:
    import json
    class Wrapper(object):
        pass
    anyjson = Wrapper()
    anyjson.loads = json.loads

import traceback
from sh import git
from peyotl import convert_nexson_format, \
                   concatenate_collections, \
                   tree_is_in_collection
from peyotl.phylesystem.git_workflows import GitWorkflowError, \
                                             validate_and_convert_nexson
from peyotl.collections_store import OWNER_ID_PATTERN, \
                               COLLECTION_ID_PATTERN
from peyotl.collections_store.validation import validate_collection
from peyotl.amendments import AMENDMENT_ID_PATTERN
from peyotl.amendments.validation import validate_amendment
from peyotl.nexson_syntax import get_empty_nexson, \
                                 extract_supporting_file_messages, \
                                 PhyloSchema, \
                                 read_as_json, \
                                 BY_ID_HONEY_BADGERFISH
from peyotl.external import import_nexson_from_treebase
from github import Github, BadCredentialsException
import api_utils
from gluon.tools import fetch
from urllib import urlencode, quote_plus
from gluon.html import web2pyHTMLParser
import re
from gluon.contrib.markdown.markdown2 import markdown
from gluon.http import HTTP
from ConfigParser import SafeConfigParser
import copy
import bleach
from bleach.sanitizer import Cleaner
from cStringIO import StringIO
_GLOG = api_utils.get_logger(None, 'ot_api.default.global')
try:
    from open_tree_tasks import call_http_json
    #_GLOG.debug('call_http_json imported')
except:
    call_http_json = None
    _GLOG.debug('call_http_json was not imported from open_tree_tasks')

_VALIDATING = True

# Cook up some reasonably strong regular expressions to detect bare
# URLs in Markdown and wrap them in hyperlinks. Adapted from
# http://stackoverflow.com/questions/1071191/detect-urls-in-a-string-and-wrap-with-a-href-tag
link_regex = re.compile(r'''
                     (?x)( # verbose identify URLs within text
                 (?<![>"]) # don't touch URLs that are already wrapped!
              (http|https) # make sure we find a resource type
                       :// # ...needs to be followed by colon-slash-slash
            (\w+[:.]?){2,} # at least two domain groups, e.g. (gnosis.)(cx)
                      (/?| # could be just the domain name (maybe w/ slash)
                [^ \n\r"]+ # or stuff then space, newline, tab, quote
                    [\w/]) # resource name ends in alphanumeric or slash
     (?=([\s\.,>)'"\]]|$)) # assert: followed by white or clause ending OR end of line
                         ) # end of match group
                           ''', re.UNICODE)
# this do-nothing version makes a sensible hyperlink
link_replace = r'\1'
# NOTE the funky constructor required to use this below

# Define a consistent cleaner to sanitize user input. We need a few
# elements that are common in our markdown but missing from the Bleach
# whitelist.
# N.B. HTML comments are stripped by default. Non-allowed tags will appear
# "naked" in output, so we can identify any bad actors.
allowed_curation_comment_tags = [u'p', u'br', u'h1', u'h2', u'h3', u'h4', u'h5', u'h6', u'hr', u'pre', u'code']  # any others?
ot_markdown_tags = list(set( bleach.sanitizer.ALLOWED_TAGS + allowed_curation_comment_tags))
ot_cleaner = Cleaner(tags=ot_markdown_tags)

def _markdown_to_html(markdown_src='', open_links_in_new_window=False):
    html = XML(markdown(markdown_src, extras={'link-patterns':None}, link_patterns=[(link_regex, link_replace)]).encode('utf-8'), sanitize=False).flatten()
    # scrub HTML output with bleach
    html = ot_cleaner.clean(html)
    if open_links_in_new_window:
        html = re.sub(r' href=',
                      r' target="_blank" href=',
                      html)
    return html

def render_markdown(src):
    # Convert POSTed Markdown to HTML (e.g., for previews in web UI)
    return _markdown_to_html( src, open_links_in_new_window=True )

def _raise_HTTP_from_msg(msg):
    raise HTTP(400, anyjson.dumps({"error": 1, "description": msg}))



def check_not_read_only():
    if api_utils.READ_ONLY_MODE:
        raise HTTP(403, json.dumps({"error": 1, "description": "phylesystem-api running in read-only mode"}))
    return True

def __deferred_push_to_gh_call(request, resource_id, doc_type='nexson', **kwargs):
    if not check_not_read_only():
        raise HTTP(500, "should raise from check_not_read_only")
    # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    if call_http_json is not None:
        # Pass the resource_id in data, so that two-part collection IDs will be recognized
        # (else the second part will trigger an unwanted JSONP response from the push)
        url = api_utils.compose_push_to_github_url(request, resource_id=None)
        auth_token = copy.copy(kwargs.get('auth_token'))
        data = {'doc_type': doc_type, 'resource_id': resource_id}
        if auth_token is not None:
            data['auth_token'] = auth_token
        call_http_json.delay(url=url, verb='PUT', data=data)
        

def index():
    response.view = 'generic.json'
    return json.dumps({
        "description": "The Open Tree API",
        "source_url": "https://github.com/OpenTreeOfLife/phylesystem-api/",
        "documentation_url": "https://github.com/OpenTreeOfLife/phylesystem-api/tree/master/docs"
    })

def trees_in_synth(*valist, **kwargs):
    """Return an "artificial" collection that contains all trees (and
    contributors) from all of the tree collections that contribute to
    synthesis.
    """
    # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    if kwargs.get('jsoncallback', None) or kwargs.get('callback', None):
        # support JSONP requests from another domain
        response.view = 'generic.jsonp'
    else:
        response.view = 'generic.json'
    coll_id_list = _get_synth_input_collection_ids()
    coll_list = []
    cds = api_utils.get_tree_collection_store(request)
    for coll_id in coll_id_list:
        try:
            coll_list.append(cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0])
        except:
            msg = 'GET of collection {} failed'.format(coll_id)
            # _LOG.exception(msg)
            raise HTTP(404, json.dumps({"error": 1, "description": msg}))
    try:
        result = concatenate_collections(coll_list)
    except:
        # _LOG.exception('concatenation of collections failed')
        e = sys.exc_info()[0]
        _raise_HTTP_from_msg(e)
    return json.dumps(result)

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

def include_tree_in_synth(study_id=None, tree_id=None, **kwargs):
    # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    if kwargs.get('jsoncallback', None) or kwargs.get('callback', None):
        # support JSONP requests from another domain
        response.view = 'generic.jsonp'
    else:
        response.view = 'generic.json'
    study_id = (study_id or "").strip()
    tree_id = (tree_id or "").strip()
    # check for empty/missing ids
    if (study_id == '') or (tree_id == ''):
        raise HTTP(400, '{"error": 1, "description": "Expecting study_id and tree_id arguments"}')
    # examine this study and tree, to confirm it exists *and* to capture its name
    sds = api_utils.get_phylesystem(request)
    found_study = None
    try:
        found_study = sds.return_doc(study_id, commit_sha=None, return_WIP_map=False)[0]
        tree_collections_by_id = found_study.get('nexml').get('treesById')
        for trees_id, trees_collection in tree_collections_by_id.items():
            trees_by_id = trees_collection.get('treeById')
            if tree_id in trees_by_id.keys():
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
            raise HTTP(404, json.dumps({"error": 1, "description": msg}))
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
            'comments': u"Added via API (include_tree_in_synth) from {p}".format(p=found_study.get('nexml')['^ot:studyPublicationReference'])
            })
        # update (or add) the decision list for this collection
        coll['decisions'] = decision_list
        # update the default collection (forces re-indexing)
        auth_info = api_utils.authenticate(**kwargs)
        owner_id = auth_info.get('login', None)
        parent_sha = kwargs.get('starting_commit_SHA', None)
        merged_sha = None  #TODO: kwargs.get('???', None)
        #_LOG.exception('======')
        #_LOG.exception(json.dumps(coll))
        #_LOG.exception('======')
        try:
            r = cds.update_existing_collection(owner_id,
                                               default_collection_id,
                                               coll,
                                               auth_info,
                                               parent_sha,
                                               merged_sha,
                                               commit_msg="Updated via API (include_tree_in_synth)")
            commit_return = r
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())

        # check for 'merge needed'?
        mn = commit_return.get('merge_needed')
        if (mn is not None) and (not mn):
            __deferred_push_to_gh_call(request, default_collection_id, doc_type='collection', **kwargs)

    # fetch and return the updated list of synth-input trees
    return trees_in_synth(kwargs)

def exclude_tree_from_synth(study_id=None, tree_id=None, **kwargs):
    # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    if kwargs.get('jsoncallback', None) or kwargs.get('callback', None):
        # support JSONP requests from another domain
        response.view = 'generic.jsonp'
    else:
        response.view = 'generic.json'
    study_id = (study_id or "").strip()
    tree_id = (tree_id or "").strip()
    # check for empty/missing ids
    if (study_id == '') or (tree_id == ''):
        raise HTTP(400, '{"error": 1, "description": "Expecting study_id and tree_id arguments"}')
    # find this tree in ANY synth-input collection; if found, remove it and update the collection
    coll_id_list = _get_synth_input_collection_ids()
    cds = api_utils.get_tree_collection_store(request)
    auth_info = api_utils.authenticate(**kwargs)
    owner_id = auth_info.get('login', None)
    for coll_id in coll_id_list:
        try:
            coll = cds.return_doc(coll_id, commit_sha=None, return_WIP_map=False)[0]
        except:
            msg = 'GET of collection {} failed'.format(coll_id)
            # _LOG.exception(msg)
            raise HTTP(404, json.dumps({"error": 1, "description": msg}))
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
            except GitWorkflowError, err:
                _raise_HTTP_from_msg(err.msg)
            except:
                raise HTTP(400, traceback.format_exc())

            # check for 'merge needed'?
            mn = commit_return.get('merge_needed')
            if (mn is not None) and (not mn):
                __deferred_push_to_gh_call(request, coll_id, doc_type='collection', **kwargs)

    # fetch and return the updated list of synth-input trees
    return trees_in_synth(kwargs)


def study_list():
    response.view = 'generic.json'
    phylesystem = api_utils.get_phylesystem(request)
    studies = phylesystem.get_study_ids()
    return json.dumps(studies)

def phylesystem_config():
    response.view = 'generic.json'
    phylesystem = api_utils.get_phylesystem(request)
    cd = phylesystem.get_configuration_dict()
    return json.dumps(cd)

def unmerged_branches():
    response.view = 'generic.json'
    phylesystem = api_utils.get_phylesystem(request)
    bl = phylesystem.get_branch_list()
    bl.sort()
    return json.dumps(bl)


def external_url():
    response.view = 'generic.json'
    try:
        study_id = request.args[0]
        # hacky way to support */external_url/STUDY_ID and */v1/external_url/STUDY_ID
        if study_id == 'external_url':
            study_id = request.args[1]
    except:
        raise HTTP(400, '{"error": 1, "description": "Expecting study_id as the argument"}')
    phylesystem = api_utils.get_phylesystem(request)
    try:
        u = phylesystem.get_public_url(study_id)
        return json.dumps({'url': u, 'study_id': study_id})
    except:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('study {} not found in external_url'.format(study_id))
        raise HTTP(404, '{"error": 1, "description": "study not found"}')

# Create a unique key with the URL and any vars (GET *or* POST) to its "query string"
# ALSO include the request method (HTTP verb) to respond to OPTIONS requests
def build_general_cache_key(request):
    return 'cached:['+ request.env.request_method.upper() +']:'+ request.url +'?'+ repr(request.vars)

@cache(key=build_general_cache_key(request), 
       time_expire=None, 
       cache_model=cache.ram)
def cached():
    """If no value was found (above) in the cache, proxy the request to its original destination"""
    ##from pprint import pprint
    # let's restrict this to the api server, to avoid shenanigans
    root_relative_url = request.env.request_uri.split('/cached/')[-1]
    ##pprint('ROOT-RELATIVE URL: ')
    ##pprint(root_relative_url)
    #@TODO this is a hack
    base_url = request.env.http_host
    base_url = api_utils.get_collections_api_base_url(request)
    fetch_url = '{}/{}'.format(base_url, root_relative_url)
    # fetch_url = '%s://%s/%s' % (request.env.wsgi_url_scheme, request.env.http_host, root_relative_url)
    
    ##pprint('PROXYING TO SIMPLE URL: ')
    ##pprint(fetch_url)

    # permissive CORS handling of requests from another domain (e.g. tree.opentreeoflife.org)
    if request.env.request_method == 'OPTIONS':
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        ##pprint('RESPONDING TO OPTIONS')
        raise HTTP(200, **(response.headers))

    # N.B. This try/except block means we'll cache errors. For now, the fix is to clear the entire cache.
    try:
        # fetch the latest IDs as JSON from remote site
        import simplejson

        if fetch_url.startswith('//'):
            # Prepend scheme to a scheme-relative URL
            fetch_url = "http:%s" % fetch_url

        fetch_args = request.vars # {'startingTaxonOTTId': ""}

        # TODO: For more flexibility, we should examine and mimic the original request (HTTP verb, headers, etc)

        # this needs to be a POST (pass fetch_args or ''); if GET, it just describes the API
        # N.B. that gluon.tools.fetch() can't be used here, since it won't send "raw" JSON data as treemachine expects
        req = urllib2.Request(url=fetch_url, data=simplejson.dumps(fetch_args), headers={"Content-Type": "application/json"}) 
        the_response = urllib2.urlopen(req).read()
        ##pprint('RESPONSE:')
        ##pprint(the_response)
        #print '...returning a sensible urllib2 response...'
        return the_response
    except urllib2.URLError, e:
        # throw a web2py exception (copying status code and message from urllib2.URLError) so we don't poison the cache!
        # REMINDER: By default, Web2py's RAM cache will ignore any response whose code doesn't match 1xx, 2xx, or 3xx!
        # NOTE that we won't cache this response, but we DO want to return its payload
        raise HTTP(e.code, e.read())
    except Exception, e:
        #print '>>> some other Exception! TRYING TO RETURN ITS VALUES IN A WEB2PY EXCEPTION...'
        raise HTTP(500, 'Unknown exception in cached call!')


def reponexsonformat():
    response.view = 'generic.json'
    phylesystem = api_utils.get_phylesystem(request)
    return json.dumps({'description': "The nexml2json property reports the version of the NexSON that is used in the document store. Using other forms of NexSON with the API is allowed, but may be slower.",
                       'nexml2json': phylesystem.repo_nexml2json})

def push_failure():
    """Return the contents of the push fail file if it exists.

    adds a boolean `pushes_succeeding` flag (True if there is no fail file)
    If this flag is False, there should also be:
        `data` utc timestamp of the push event that first failed
        `study` the study that triggered the first failing push event
        `commit` the master commit SHA of the working dir at the time of the first failure
        `stacktrace`: the stacktrace of the push_study_to_remote operation that failed.
    If `pushes_succeeded` is False, but there is only a message field, then another
        thread may have rectified the push problems while this operation was trying
        to report the errors. In this case, you should call this function again.
        Report a bug if it has not reverted to `pushes_succeeding=True.
    """

    response.view = 'generic.json'
    fail_file = api_utils.get_failed_push_filepath(request)
    if os.path.exists(fail_file):
        try:
            blob = read_as_json(fail_file)
        except:
            blob = {'message': 'could not read push fail file'}
        blob['pushes_succeeding'] = False
    else:
        blob = {'pushes_succeeding': True}
    blob['doc_type'] = request.vars.get('doc_type', 'nexson')
    return json.dumps(blob)


def collections(*args, **kwargs):
    """Handle an incoming URL targeting /v2/collections/
    This includes:
        /v2/collections/find_collections
        /v2/collections/find_trees
        /v2/collections/properties
    """
    if request.env.request_method == 'OPTIONS':
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, T("OPTIONS!"), **(response.headers))
    # N.B. other request methods don't really matter for these functions!
    # extract and validate the intended API call
    assert request.args[0].lower() == 'collections'
    if len(request.args) < 2:
        raise HTTP(404, T('No method specified! Try collections/find_collections, find_trees, or properties'))
    api_call = request.args[1]   # ignore anything later in the URL
    if api_call == 'find_collections':
        # TODO: proxy to oti? or drop 'collections' here and re-route this (in apache config)?
        # For now, let's just return all collections (complete JSON)
        response.view = 'generic.json'
        docstore = api_utils.get_tree_collection_store(request)
        # Convert these to more closely resemble the output of find_all_studies
        collection_list = []
        for id, props in docstore.iter_doc_objs():
            # reckon and add 'lastModified' property, based on commit history?
            latest_commit = docstore.get_version_history_for_doc_id(id)[0]
            props.update({
                'id': id,
                'lastModified': {
                        'author_name': latest_commit.get('author_name'),
                        'relative_date': latest_commit.get('relative_date'),
                        'display_date': latest_commit.get('date'),
                        'ISO_date': latest_commit.get('date_ISO_8601'),
                        'sha': latest_commit.get('id')  # this is the commit hash
                        }
                })
            collection_list.append(props)
        return json.dumps(collection_list)
    if api_call == 'find_trees':
        # TODO: proxy to oti? see above, and also controllers/studies.py > find_trees()
        raise HTTP(200, T("Now we'd list all collections holding trees that match the criteria provided!"))
    elif api_call == 'collection_list':
        response.view = 'generic.json'
        docstore = api_utils.get_tree_collection_store(request)
        ids = docstore.get_collection_ids()
        return json.dumps(ids)
    elif api_call == 'properties':
        # TODO: proxy to oti? or drop 'collections' here and re-route this (in apache config)?
        raise HTTP(200, T("Now we'd list all searchable properties in tree collections!"))
    elif api_call == 'store_config':
        response.view = 'generic.json'
        docstore = api_utils.get_tree_collection_store(request)
        cd = docstore.get_configuration_dict()
        return json.dumps(cd)
    elif api_call == 'push_failure':
        # this should find a type-specific PUSH_FAILURE file
        request.vars['doc_type'] = 'collection'
        return push_failure()   
    raise HTTP(404, T('No such method as collections/{}'.format(api_call)))

def __extract_json_from_http_call(request, data_field_name='data', **kwargs):
    """Returns the json blob (as a deserialized object) from `kwargs` or the request.body"""
    json_obj = None
    try:
        # check for kwarg data_field_name, or load the full request body
        if data_field_name in kwargs:
            json_obj = kwargs.get(data_field_name, {})
        else:
            json_obj = request.body.read()

        if not isinstance(json_obj, dict):
            json_obj = json.loads(json_obj)
        if data_field_name in json_obj:
            json_obj = json_obj[data_field_name]
    except:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('Exception getting JSON content in __extract_json_from_http_call')
        raise HTTP(400, json.dumps({"error": 1, "description": 'no collection JSON found in request'}))
    return json_obj

def collection(*args, **kwargs):
    """Handle an incoming URL targeting /v2/collection/{COLLECTION_ID}
    Use our typical mapping of HTTP verbs to (sort of) CRUD actions.
    """
    # _LOG = api_utils.get_logger(request, 'ot_api.collection')
    if request.env.request_method == 'OPTIONS':
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, T("single-collection OPTIONS!"), **(response.headers))

    def __extract_and_validate_collection(request, kwargs):
        from pprint import pprint
        try:
            collection_obj = __extract_json_from_http_call(request, data_field_name='json', **kwargs)
        except HTTP, err:
            # payload not found
            return None, None, None
        try:
            errors, collection_adaptor = validate_collection(collection_obj)
        except HTTP, err:
            # _LOG.exception('JSON payload failed validation (raising HTTP response)')
            pprint(err)
            raise err
        except Exception, err:
            # _LOG.exception('JSON payload failed validation (reporting err.msg)')
            pprint(err)
            try:
                msg = err.get('msg', 'No message found')
            except:
                msg = str(err)
            _raise_HTTP_from_msg(msg)
        if len(errors) > 0:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            msg = 'JSON payload failed validation with {nerrors} errors:\n{errors}'.format(nerrors=len(errors), errors='\n  '.join(errors))
            # _LOG.exception(msg)
            _raise_HTTP_from_msg(msg)
        return collection_obj, errors, collection_adaptor

    assert request.args[0].lower() == 'collection'
    # check for full or partial collection ID
    owner_id = None
    collection_id = None
    if len(request.args) > 1:
        # for a new collection, we might have just the owner's id (GitHub username)
        owner_id = request.args[1]
        if not OWNER_ID_PATTERN.match(owner_id):
            raise HTTP(400, json.dumps({"error": 1, "description": "invalid owner ID ({}) provided".format(owner_id)}))
    if len(request.args) > 2:
        collection_id = ('/').join(request.args[1:3])
        if not COLLECTION_ID_PATTERN.match(collection_id):
            #raise HTTP(400, json.dumps({"error": 1, "description": 'invalid collection ID provided'}))
            # ignore the submitted id and generate a new one
            collection_id = None
    elif request.env.request_method != 'POST':
        # N.B. this id is optional when creating a new collection
        raise HTTP(400, json.dumps({"error": 1, "description": 'collection ID expected after "collection/"'}))

    # fetch and parse the JSON payload, if any 
    collection_obj, collection_errors, collection_adapter = __extract_and_validate_collection(request,
                                                                                              kwargs)
    if (collection_obj is None) and request.env.request_method in ('POST','PUT'):
        raise HTTP(400, json.dumps({"error": 1, "description": "collection JSON expected for HTTP method {}".format(request.env.request_method) }))

    auth_info = None
    if owner_id is None:
        # set this explicitly to the logged-in userid (make sure the user is allowed!)
        auth_info = api_utils.authenticate(**kwargs)
        owner_id = auth_info.get('login', None)
        if owner_id is None:
            raise HTTP(400, json.dumps({"error": 1, "description": "no GitHub userid found for HTTP method {}".format(request.env.request_method) }))
    if collection_id is None:
        # try to extract a usable collection ID from the JSON payload (confirm owner_id against above)
        url = collection_obj.get('url', None)
        if url is None:
            raise HTTP(400, json.dumps({"error": 1, "description": "no collection URL provided in query string or JSON payload"}))
        try:
            collection_id = url.split('/collection/')[1]
        except:
            # _LOG.exception('{} failed'.format(request.env.request_method))
            raise HTTP(404, json.dumps({"error": 1, "description": "invalid URL, no collection id found: {}".format(url)}))
        try:
            assert collection_id.split('/')[0] == owner_id
        except:
            # _LOG.exception('{} failed'.format(request.env.request_method))
            raise HTTP(404, json.dumps({"error": 1, "description": "collection URL in JSON doesn't match logged-in user: {}".format(url)}))

    # some request types imply git commits; gather any user-provided commit message
    try:
        commit_msg = kwargs.get('commit_msg','')
        if commit_msg.strip() == '':
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None
        
    if kwargs.get('jsoncallback', None) or kwargs.get('callback', None):
        # support JSONP requests from another domain
        response.view = 'generic.jsonp'

    if request.env.request_method == 'GET':
        # fetch the current collection JSON
        # _LOG.debug('GET /v2/collection/{}'.format(str(collection_id)))
        version_history = None
        comment_html = None
        parent_sha = kwargs.get('starting_commit_SHA', None)
        # _LOG.debug('parent_sha = {}'.format(parent_sha))
        # return the correct nexson of study_id, using the specified view
        collections = api_utils.get_tree_collection_store(request)
        try:
            r = collections.return_doc(collection_id, commit_sha=parent_sha, return_WIP_map=True)
        except:
            # _LOG.exception('GET failed')
            raise HTTP(404, json.dumps({"error": 1, "description": "Collection '{}' GET failure".format(collection_id)}))
        try:
            collection_json, head_sha, wip_map = r
            ## if returning_full_study:  # TODO: offer bare vs. full output (w/ history, etc)
            version_history = collections.get_version_history_for_doc_id(collection_id)
            try:
                # pre-render internal description (assumes markdown!)
                comment_html = _markdown_to_html(collection_json['description'], open_links_in_new_window=True )
            except:
                comment_html = ''
        except:
            # _LOG.exception('GET failed')
            e = sys.exc_info()[0]
            _raise_HTTP_from_msg(e)
        if not collection_json:
            raise HTTP(404, "Collection '{s}' has no JSON data!".format(s=collection_id))
        # add/restore the url field (using the visible fetch URL)
        base_url = api_utils.get_collections_api_base_url(request)
        collection_json['url'] = '{b}/v2/collection/{i}'.format(b=base_url,
                                                            i=collection_id)
        try:
            external_url = collections.get_public_url(collection_id)
        except:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            # _LOG.exception('collection {} not found in external_url'.format(collection))
            external_url = 'NOT FOUND'
        result = {'sha': head_sha,
                 'data': collection_json,
                 'branch2sha': wip_map,
                 'commentHTML': comment_html,
                 'external_url': external_url,
                 }
        if version_history:
            result['versionHistory'] = version_history

            # reckon and add 'lastModified' property, based on commit history?
            latest_commit = version_history[0]
            last_modified = {
                'author_name': latest_commit.get('author_name'),
                'relative_date': latest_commit.get('relative_date'),
                'display_date': latest_commit.get('date'),
                'ISO_date': latest_commit.get('date_ISO_8601'),
                'sha': latest_commit.get('id')  # this is the commit hash
            }
            result['lastModified'] = last_modified
        return result

    if request.env.request_method == 'PUT':
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only") 
        # update an existing collection with the data provided
        # _LOG = api_utils.get_logger(request, 'ot_api.default.collections.PUT')
        auth_info = auth_info or api_utils.authenticate(**kwargs)
        # submit new json for this id, and read the results
        parent_sha = kwargs.get('starting_commit_SHA', None)
        merged_sha = None  #TODO: kwargs.get('???', None)
        docstore = api_utils.get_tree_collection_store(request)
        try:
            r = docstore.update_existing_collection(owner_id, 
                                                    collection_id,
                                                    collection_obj, 
                                                    auth_info,
                                                    parent_sha,
                                                    merged_sha, 
                                                    commit_msg=commit_msg)
            commit_return = r
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())

        # check for 'merge needed'?
        mn = commit_return.get('merge_needed')
        if (mn is not None) and (not mn):
            __deferred_push_to_gh_call(request, collection_id, doc_type='collection', **kwargs)
        # Add updated commit history to the blob
        commit_return['versionHistory'] = docstore.get_version_history_for_doc_id(collection_id)
        return commit_return
        #
        #        parent_sha = kwargs.get('starting_commit_SHA')
        #        if parent_sha is None:
        #            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        #        try:
        #            commit_msg = kwargs.get('commit_msg','')
        #            if commit_msg.strip() == '':
        #                # git rejects empty commit messages
        #                commit_msg = None
        #        except:
        #            commit_msg = None
        #        master_file_blob_included = kwargs.get('merged_SHA')
        #        msg = 'PUT to collection {} for starting_commit_SHA = {} and merged_SHA = {}'
        #        _LOG.debug(msg.format(collection_id,
        #                              parent_sha,
        #                              str(master_file_blob_included)))
        #

        #         try:
        #             gd = phylesystem.create_git_action(resource_id)
        #         except KeyError, err:
        #             _LOG.debug('PUT failed in create_git_action (probably a bad collection ID)')
        #             _raise_HTTP_from_msg("invalid collection ID, please check the URL")
        #         except GitWorkflowError, err:
        #             _LOG.debug('PUT failed in create_git_action: {}'.format(err.msg))
        #             _raise_HTTP_from_msg(err.msg)
        #         except:
        #             raise HTTP(400, traceback.format_exc())

    if request.env.request_method == 'POST':
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        # Create a new collection with the data provided
        # _LOG = api_utils.get_logger(request, 'ot_api.default.collections.POST')
        auth_info = auth_info or api_utils.authenticate(**kwargs)
        # submit the json and proposed id (if any), and read the results
        docstore = api_utils.get_tree_collection_store(request)
        try:
            r = docstore.add_new_collection(owner_id, 
                                            collection_obj, 
                                            auth_info,
                                            collection_id, 
                                            commit_msg=commit_msg)
            new_collection_id, commit_return = r
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())
        if commit_return['error'] != 0:
            # _LOG.debug('add_new_collection failed with error code')
            raise HTTP(400, json.dumps(commit_return))
        __deferred_push_to_gh_call(request, new_collection_id, doc_type='collection', **kwargs)
        return commit_return

    if request.env.request_method == 'DELETE':
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        # remove this collection from the docstore
        # _LOG = api_utils.get_logger(request, 'ot_api.default.collections.POST')
        auth_info = auth_info or api_utils.authenticate(**kwargs)
        docstore = api_utils.get_tree_collection_store(request)
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        try:
            x = docstore.delete_collection(collection_id, 
                                           auth_info, 
                                           parent_sha, 
                                           commit_msg=commit_msg)
            if x.get('error') == 0:
                __deferred_push_to_gh_call(request, None, doc_type='collection', **kwargs)
            return x
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            # _LOG.exception('Unknown error in collection deletion')
            # raise HTTP(400, traceback.format_exc())
            raise HTTP(400, json.dumps({"error": 1, "description": 'Unknown error in collection deletion'}))

    raise HTTP(500, T("Unknown HTTP method '{}'".format(request.env.request_method)))


# TAXONOMIC AMENDMENTS

def amendments(*args, **kwargs):
    """Handle an incoming URL targeting /v3/amendments/
    This includes:
        /v3/amendments/list_all
        /v3/amendments/store_config
        /v3/amendments/push_failure
    """
    if request.env.request_method == 'OPTIONS':
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, T("OPTIONS!"), **(response.headers))
    # N.B. other request methods don't really matter for these functions!
    # extract and validate the intended API call
    assert request.args[0].lower() == 'amendments'
    if len(request.args) < 2:
        raise HTTP(404, T('No method specified! Try amendments/list_all, store_config, or push_failure'))
    api_call = request.args[1]   # ignore anything later in the URL
    if api_call == 'list_all':
        # For now, let's just return all amendments (complete JSON)
        response.view = 'generic.json'
        docstore = api_utils.get_taxonomic_amendment_store(request)
        # Convert these to more closely resemble the output of find_all_studies
        amendment_list = []
        for id, props in docstore.iter_doc_objs():
            # reckon and add 'lastModified' property, based on commit history?
            latest_commit = docstore.get_version_history_for_doc_id(id)[0]
            props.update({
                'id': id,
                'lastModified': {
                        'author_name': latest_commit.get('author_name'),
                        'relative_date': latest_commit.get('relative_date'),
                        'display_date': latest_commit.get('date'),
                        'ISO_date': latest_commit.get('date_ISO_8601'),
                        'sha': latest_commit.get('id')  # this is the commit hash
                        }
                })
            amendment_list.append(props)
        return json.dumps(amendment_list)
    elif api_call == 'amendment_list':
        response.view = 'generic.json'
        docstore = api_utils.get_taxonomic_amendment_store(request)
        ids = docstore.get_amendment_ids()
        return json.dumps(ids)
    elif api_call == 'store_config':
        response.view = 'generic.json'
        docstore = api_utils.get_taxonomic_amendment_store(request)
        cd = docstore.get_configuration_dict()
        return json.dumps(cd)
    elif api_call == 'push_failure':
        # this should find a type-specific PUSH_FAILURE file
        request.vars['doc_type'] = 'amendment'
        return push_failure()
    raise HTTP(404, T('No such method as amendments/{}'.format(api_call)))

def amendment(*args, **kwargs):
    """Handle an incoming URL targeting /v3/amendment/{AMENDMENT_ID}
    Use our typical mapping of HTTP verbs to (sort of) CRUD actions.
    """
    # _LOG = api_utils.get_logger(request, 'ot_api.amendment')
    if request.env.request_method == 'OPTIONS':
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, T("single-amendment OPTIONS!"), **(response.headers))

    def __extract_and_validate_amendment(request, kwargs):
        from pprint import pprint
        try:
            amendment_obj = __extract_json_from_http_call(request, data_field_name='json', **kwargs)
        except HTTP, err:
            # payload not found
            return None, None, None
        try:
            errors, amendment_adaptor = validate_amendment(amendment_obj)
        except HTTP, err:
            #_LOG.exception('JSON payload failed validation (raising HTTP response)')
            # pprint(err)
            raise err
        except Exception, err:
            # _LOG.exception('JSON payload failed validation (reporting err.msg)')
            # pprint(err)
            try:
                msg = err.get('msg', 'No message found')
            except:
                msg = str(err)
            _raise_HTTP_from_msg(msg)
        if len(errors) > 0:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            msg = 'JSON payload failed validation with {nerrors} errors:\n{errors}'.format(nerrors=len(errors), errors='\n  '.join(errors))
            # _LOG.exception(msg)
            _raise_HTTP_from_msg(msg)
        return amendment_obj, errors, amendment_adaptor

    assert request.args[0].lower() == 'amendment'
    # check for an existing amendment ID
    amendment_id = None
    if len(request.args) > 1:
        amendment_id = request.args[1]
        if not AMENDMENT_ID_PATTERN.match(amendment_id):
            raise HTTP(400, json.dumps({"error": 1, "description": "invalid amendment ID ({}) provided".format(amendment_id)}))
            # TODO: OR ignore the submitted id and generate a new one
            #amendment_id = None

    elif request.env.request_method != 'POST':
        # N.B. this id is optional when creating a new amendment
        raise HTTP(400, json.dumps({"error": 1, "description": 'amendment ID expected after "amendment/"'}))

    # fetch and parse the JSON payload, if any
    amendment_obj, amendment_errors, amendment_adapter = __extract_and_validate_amendment(request,
                                                                                              kwargs)
    if (amendment_obj is None) and request.env.request_method in ('POST','PUT'):
        raise HTTP(400, json.dumps({"error": 1, "description": "amendment JSON expected for HTTP method {}".format(request.env.request_method) }))

    if request.env.request_method != 'GET':
        # all other methods require authentication
        auth_info = api_utils.authenticate(**kwargs)

    # some request types imply git commits; gather any user-provided commit message
    try:
        commit_msg = kwargs.get('commit_msg','')
        if commit_msg.strip() == '':
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    if kwargs.get('jsoncallback', None) or kwargs.get('callback', None):
        # support JSONP requests from another domain
        response.view = 'generic.jsonp'

    if request.env.request_method == 'GET':
        # fetch the current amendment JSON
        # _LOG.debug('GET /v2/amendment/{}'.format(str(amendment_id)))
        version_history = None
        comment_html = None
        parent_sha = kwargs.get('starting_commit_SHA', None)
        # _LOG.debug('parent_sha = {}'.format(parent_sha))
        # return the correct nexson of study_id, using the specified view
        amendments = api_utils.get_taxonomic_amendment_store(request)
        try:
            r = amendments.return_doc(amendment_id, commit_sha=parent_sha, return_WIP_map=True)
        except:
            # _LOG.exception('GET failed')
            raise HTTP(404, json.dumps({"error": 1, "description": "Amendment '{}' GET failure".format(amendment_id)}))
        try:
            amendment_json, head_sha, wip_map = r
            ## if returning_full_study:  # TODO: offer bare vs. full output (w/ history, etc)
            version_history = amendments.get_version_history_for_doc_id(amendment_id)
        except:
            # _LOG.exception('GET failed')
            e = sys.exc_info()[0]
            _raise_HTTP_from_msg(e)
        if not amendment_json:
            raise HTTP(404, "Amendment '{s}' has no JSON data!".format(s=amendment_id))

        try:
            external_url = amendments.get_public_url(amendment_id)
        except:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            # _LOG.exception('amendment {} not found in external_url'.format(amendment))
            external_url = 'NOT FOUND'
        result = {'sha': head_sha,
                 'data': amendment_json,
                 'branch2sha': wip_map,
                 'external_url': external_url,
                 }
        if version_history:
            result['versionHistory'] = version_history
        return result

    if request.env.request_method == 'PUT':
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        # update an existing amendment with the data provided
        # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.PUT')
        # submit new json for this id, and read the results
        parent_sha = kwargs.get('starting_commit_SHA', None)
        merged_sha = None  #TODO: kwargs.get('???', None)
        docstore = api_utils.get_taxonomic_amendment_store(request)
        try:
            r = docstore.update_existing_amendment(amendment_id,
                                                   amendment_obj,
                                                   auth_info,
                                                   parent_sha,
                                                   merged_sha,
                                                   commit_msg=commit_msg)
            commit_return = r
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())

        # check for 'merge needed'?
        mn = commit_return.get('merge_needed')
        if (mn is not None) and (not mn):
            __deferred_push_to_gh_call(request, amendment_id, doc_type='amendment', **kwargs)
        return commit_return

    if request.env.request_method == 'POST':
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        # Create a new amendment with the data provided
        # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.POST')
        # submit the json and proposed id (if any), and read the results
        docstore = api_utils.get_taxonomic_amendment_store(request)

        # N.B. add_new_amendment below takes care of minting new ottids,
        # assigning them to new taxa, and returning a per-taxon mapping to the
        # caller. It will assign the new amendment id accordingly!
        try:
            r = docstore.add_new_amendment(amendment_obj,
                                           auth_info,
                                           commit_msg=commit_msg)
            new_amendment_id, commit_return = r
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())
        if commit_return['error'] != 0:
            # _LOG.debug('add_new_amendment failed with error code')
            raise HTTP(400, json.dumps(commit_return))
        __deferred_push_to_gh_call(request, new_amendment_id, doc_type='amendment', **kwargs)
        return commit_return

    if request.env.request_method == 'DELETE':
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        # remove this amendment from the docstore
        # _LOG = api_utils.get_logger(request, 'ot_api.default.amendments.POST')
        docstore = api_utils.get_taxonomic_amendment_store(request)
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        try:
            x = docstore.delete_amendment(amendment_id,
                                          auth_info,
                                          parent_sha,
                                          commit_msg=commit_msg)
            if x.get('error') == 0:
                __deferred_push_to_gh_call(request, None, doc_type='amendment', **kwargs)
            return x
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            # _LOG.exception('Unknown error in amendment deletion')
            raise HTTP(400, traceback.format_exc())
            #raise HTTP(400, json.dumps({"error": 1, "description": 'Unknown error in amendment deletion'}))

    raise HTTP(500, T("Unknown HTTP method '{}'".format(request.env.request_method)))


# Names here will intercept GET and POST requests to /v1/{METHOD_NAME}
# This allows us to normalize all API method URLs under v1/, even for
# non-RESTful methods.
_route_tag2func = {'index':index,
                   'trees_in_synth': trees_in_synth,
                   'include_tree_in_synth': include_tree_in_synth,
                   'exclude_tree_from_synth': exclude_tree_from_synth,
                   'study_list': study_list,
                   'phylesystem_config': phylesystem_config,
                   'unmerged_branches': unmerged_branches,
                   'external_url': external_url,
                   'push_failure': push_failure,
                   'repo_nexson_format': reponexsonformat,
                   'reponexsonformat': reponexsonformat,
                   'render_markdown': render_markdown,
                   # handle minor resource types based on identifying paths
                   # NOTE singular vs. plural forms
                   'collections': collections,
                   'collection': collection,
                   'amendments': amendments,
                   'amendment': amendment,
                   #TODO: 'following': following,
                  }

def _fetch_shard_name(study_id):
    phylesystem = api_utils.get_phylesystem(request)
    try:
            shard_name, path_frag = phylesystem.get_repo_and_path_fragment(study_id)
            return shard_name
    except:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            # _LOG.debug('_fetch_shard_name failed for study {}'.format(study_id))
            return None

def _fetch_duplicate_study_ids(study_DOI=None, study_ID=None):
    # Use the oti (docstore index) service to see if there are other studies in
    # the collection with the same DOI; return the IDs of any duplicate studies
    # found, or an empty list if there are no dupes.
    if not study_DOI:
        # if no DOI exists, there are no known duplicates
        return [ ]
    oti_base_url = api_utils.get_oti_base_url(request)
    fetch_url = '%s/v3/studies/find_studies' % oti_base_url
    # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    try:
        #_LOG.debug('trying with requests')
        data = json.dumps({
                "property": "ot:studyPublication",
                "value": study_DOI,
                "exact": False})
        # _LOG.debug('data is {}'.format(data))
        r = requests.post(url = fetch_url, data = data)
        response_json = r.json()
    except:
        # _LOG.exception('fetch duplicate dois failed')
        raise HTTP(400, traceback.format_exc())
    duplicate_study_ids = [x['ot:studyId'] for x in response_json['matched_studies']]
    # Remove this study's ID; any others that remain are duplicates
    try:
        duplicate_study_ids.remove(study_ID)
    except ValueError:
        # ignore error, if oti is lagging and doesn't have this study yet
        pass
    return duplicate_study_ids


@request.restful()
def v1():
    "The OpenTree API v1"
    _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    response.view = 'generic.json'

    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = 86400  # cache for a day

    phylesystem = api_utils.get_phylesystem(request)
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
    #_LOG.debug('Max file size set to {}, max num trees set to {}'.format(max_filesize, max_num_trees))
    repo_nexml2json = phylesystem.repo_nexml2json
    LOG.debug("phylesystem created with repo_nexml2json={}".format(repo_nexml2json))
    def __validate_output_nexml2json(kwargs, resource, type_ext, content_id=None):
        msg = None
        if 'output_nexml2json' not in kwargs:
            kwargs['output_nexml2json'] = '0.0.0'
        biv = kwargs.get('bracket_ingroup')
        if biv and (isinstance(biv, str) or isinstance(biv, unicode)):
            if biv.lower() in ['f', 'false', '0']:
                kwargs['bracket_ingroup'] = False
            else:
                kwargs['bracket_ingroup'] = True
        try:
            schema = PhyloSchema(schema=kwargs.get('format'),
                                 type_ext=type_ext,
                                 content=resource,
                                 content_id=content_id,
                                 repo_nexml2json=repo_nexml2json,
                                 **kwargs)
            if not schema.can_convert_from(resource):
                msg = 'Cannot convert from {s} to {d}'.format(s=repo_nexml2json,
                                                              d=schema.description)
        except ValueError, x:
            _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            msg = str(x)
            #_LOG.exception('GET failing: {m}'.format(m=msg))
        if msg:
            _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            _LOG.debug('output sniffing err msg = ' + msg)
            raise HTTP(400, json.dumps({"error": 1, "description": msg}))
        return schema
    def __finish_write_verb(phylesystem,
                            git_data, 
                            nexson,
                            resource_id,
                            auth_info,
                            adaptor,
                            annotation,
                            parent_sha,
                            commit_msg='',
                            master_file_blob_included=None):
        '''Called by PUT and POST handlers to avoid code repetition.'''
        # global TIMING
        #TODO, need to make this spawn a thread to do the second commit rather than block
        a = phylesystem.annotate_and_write(git_data, 
                                           nexson,
                                           resource_id,
                                           auth_info,
                                           adaptor,
                                           annotation,
                                           parent_sha,
                                           commit_msg,
                                           master_file_blob_included)
        annotated_commit = a
        # TIMING = api_utils.log_time_diff(_LOG, 'annotated commit', TIMING)
        if annotated_commit['error'] != 0:
             _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
             _LOG.debug('annotated_commit failed')
            raise HTTP(400, json.dumps(annotated_commit))
        return annotated_commit

    def GET(resource,
            resource_id=None,
            subresource=None,
            subresource_id=None,
            jsoncallback=None,
            callback=None,
            _=None,
            **kwargs):
        "OpenTree API methods relating to reading"
        _LOG = api_utils.get_logger(request, 'ot_api.default.v1.GET')
        delegate = _route_tag2func.get(resource)
        if delegate:
            return delegate(**kwargs)
        valid_resources = ('study', )
        if not resource.lower() == 'study':
            raise HTTP(400, json.dumps({"error": 1,
                                        "description": 'resource requested not in list of valid resources: %s' % valid_resources }))
        if resource_id is None:
            raise HTTP(400, json.dumps({"error": 1, "description": 'study ID expected after "study/"'}))
        valid_subresources = ('tree', 'meta', 'otus', 'otu', 'otumap')
        _LOG.debug('GET default/v1/{}/{}'.format(str(resource), str(resource_id)))
        returning_full_study = False
        returning_tree = False
        content_id = None
        version_history = None
        comment_html = None
        if request.extension not in('html', 'json'):
            type_ext = '.' + request.extension
            _LOG.debug('type_ext is {}'.format(str(type_ext)))
        else:
            type_ext = None
        if subresource is None:
            returning_full_study = True
            return_type = 'study'
        elif subresource == 'tree':
            return_type = 'tree'
            returning_tree = True
            content_id = subresource_id
        elif subresource == 'subtree':
            subtree_id = kwargs.get('subtree_id')
            if subtree_id is None:
                raise HTTP(400, json.dumps({"error": 1,
                                            "description": 'subtree resource requires a study_id and tree_id in the URL and a subtree_id parameter'}))
            return_type = 'subtree'
            returning_tree = True
            content_id = (subresource_id, subtree_id)
        elif subresource in ['file', 'meta', 'otus', 'otu', 'otumap']:
            if subresource != 'meta':
                content_id = subresource_id
            return_type = subresource
        else:
            raise HTTP(400, json.dumps({"error": 1,
                                        "description": 'subresource requested not in list of valid resources: %s' % ' '.join(valid_subresources)}))
        out_schema = __validate_output_nexml2json(kwargs,
                                                  return_type,
                                                  type_ext,
                                                  content_id=content_id)
        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'
        parent_sha = kwargs.get('starting_commit_SHA')
        # _LOG.debug('parent_sha = {}'.format(parent_sha))
        # return the correct nexson of study_id, using the specified view
        phylesystem = api_utils.get_phylesystem(request)
        try:
            r = phylesystem.return_study(resource_id, commit_sha=parent_sha, return_WIP_map=True)
        except:
            # _LOG.exception('GET failed')
            raise HTTP(404, json.dumps({"error": 1, "description": 'Study #%s GET failure' % resource_id}))
        try:
            study_nexson, head_sha, wip_map = r
            if returning_full_study:
                blob_sha = phylesystem.get_blob_sha_for_study_id(resource_id, head_sha)
                phylesystem.add_validation_annotation(study_nexson, blob_sha)
                version_history = phylesystem.get_version_history_for_study_id(resource_id)
                try:
                    comment_html = _markdown_to_html(study_nexson['nexml']['^ot:comment'], open_links_in_new_window=True )
                except:
                    comment_html = ''
        except:
            # _LOG.exception('GET failed')
            e = sys.exc_info()[0]
            _raise_HTTP_from_msg(e)
        if subresource == 'file':
            m_list = extract_supporting_file_messages(study_nexson)
            if subresource_id is None:
                r = []
                for m in m_list:
                    files = m.get('data', {}).get('files', {}).get('file', [])
                    for f in files:
                        if '@url' in f:
                            r.append({'id': m['@id'],
                                      'filename': f.get('@filename', ''),
                                      'url_fragment': f['@url']})
                            break
                return json.dumps(r)
            else:
                try:
                    matching = None
                    for m in m_list:
                        if m['@id'] == subresource_id:
                            matching = m
                            break
                    if matching is None:
                        raise HTTP(404, 'No file with id="{f}" found in study="{s}"'.format(f=subresource_id, s=resource_id))
                    u = None
                    files = m.get('data', {}).get('files', {}).get('file', [])
                    for f in files:
                        if '@url' in f:
                            u = f['@url']
                            break
                    if u is None:
                        raise HTTP(404, 'No @url found in the message with id="{f}" found in study="{s}"'.format(f=subresource_id, s=resource_id))
                    #TEMPORARY HACK TODO
                    u = u.replace('uploadid=', 'uploadId=')
                    #TODO: should not hard-code this, I suppose... (but not doing so requires more config...)
                    if u.startswith('/curator'):
                        u = 'https://tree.opentreeoflife.org' + u
                    response.headers['Content-Type'] = 'text/plain'
                    fetched = requests.get(u)
                    fetched.raise_for_status()
                    return fetched.text
                except Exception as x:
                    # _LOG.exception('file_get failed')
                    raise HTTP(404, 'Could not retrieve file. Exception: "{}"'.format(str(x)))
        elif out_schema.format_str == 'nexson' and out_schema.version == repo_nexml2json:
            result_data = study_nexson
        else:
            try:
                serialize = not out_schema.is_json()
                src_schema = PhyloSchema('nexson', version=repo_nexml2json)
                result_data = out_schema.convert(study_nexson,
                                                 serialize=serialize,
                                                 src_schema=src_schema)
            except:
                msg = "Exception in coercing to the required NexSON version for validation. "
                # _LOG.exception(msg)
                raise HTTP(400, msg)
        if not result_data:
            raise HTTP(404, 'subresource "{r}/{t}" not found in study "{s}"'.format(r=subresource,
                                                                                    t=subresource_id,
                                                                                    s=resource_id))

        if returning_full_study and out_schema.is_json():
            try:
                study_DOI = study_nexson['nexml']['^ot:studyPublication']['@href']
            except KeyError:
                study_DOI = None
            try:
                duplicate_study_ids = _fetch_duplicate_study_ids(study_DOI, resource_id)
            except:
                # _LOG.exception('call to OTI check for duplicate DOIs failed')
                duplicate_study_ids = None

            try:
                shard_name = _fetch_shard_name(resource_id)
            except:
                # _LOG.exception('check for shard name failed')
                shard_name = None

            result = {'sha': head_sha,
                     'data': result_data,
                     'branch2sha': wip_map,
                     'commentHTML': comment_html,
                     }
            if duplicate_study_ids is not None:
                result['duplicateStudyIDs'] = duplicate_study_ids
            if shard_name:
                result['shardName'] = shard_name
            if version_history:
                result['versionHistory'] = version_history
            return result
        else:
            return result_data

    def POST(resource, resource_id=None, _method='POST', **kwargs):
        "Open Tree API methods relating to creating (and importing) resources"
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        delegate = _route_tag2func.get(resource)
        if delegate:
            return delegate(**kwargs)
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1.POST')
        # support JSONP request from another domain
        if kwargs.get('jsoncallback', None) or kwargs.get('callback', None):
            response.view = 'generic.jsonp'
        # check for HTTP method override (passed on query string)
        if _method == 'PUT':
            PUT(resource, resource_id, kwargs)
        elif _method == 'DELETE':
            DELETE(resource, resource_id, kwargs)
        if not resource == 'study':
            raise HTTP(400, json.dumps({"error":1,
                                        "description": "Only the creation of new studies is currently supported"}))
        auth_info = api_utils.authenticate(**kwargs)
        # Studies that were created in phylografter, can be added by
        #   POSTing the content with resource_id
        new_study_id = resource_id
        if new_study_id is not None:
            try:
                int(new_study_id)
            except:
                new_study_id = 'pg_' + new_study_id
            else:
                try:
                    new_study_id.startswith('pg_')
                except:
                    raise HTTP(400, 'Use of the resource_id to specify a study ID is limited to phylografter studies')
            bundle = __extract_and_validate_nexson(request,
                                                   repo_nexml2json,
                                                   kwargs)
            new_study_nexson = bundle[0]
        else:
            # we're creating a new study (possibly with import instructions in the payload)
            import_from_location = kwargs.get('import_from_location', '')
            treebase_id = kwargs.get('treebase_id', '')
            nexml_fetch_url = kwargs.get('nexml_fetch_url', '')
            nexml_pasted_string = kwargs.get('nexml_pasted_string', '')
            publication_doi = kwargs.get('publication_DOI', '')
            # if a URL or something other than a valid DOI was entered, don't submit it to crossref API
            publication_doi_for_crossref = __make_valid_DOI(publication_doi) or None
            publication_ref = kwargs.get('publication_reference', '')
            # is the submitter explicity applying the CC0 waiver to a new study?
            cc0_agreement = (kwargs.get('chosen_license', '') == 'apply-new-CC0-waiver' and
                             kwargs.get('cc0_agreement', '') == 'true')
            # look for the chosen import method, e.g,
            # 'import-method-PUBLICATION_DOI' or 'import-method-MANUAL_ENTRY'
            import_method = kwargs.get('import_method', '')

            ##dryad_DOI = kwargs.get('dryad_DOI', '')

            app_name = request.application
            # add known values for its metatags
            meta_publication_reference = None

            # Create initial study NexSON using the chosen import method.
            #
            # N.B. We're currently using a streamlined creation path with just
            # two methods (TreeBASE ID and publication DOI). But let's keep the
            # logic for others, just in case we revert based on user feedback.
            importing_from_treebase_id = (import_method == 'import-method-TREEBASE_ID' and treebase_id)
            importing_from_nexml_fetch = (import_method == 'import-method-NEXML' and nexml_fetch_url)
            importing_from_post_arg = (import_method == 'import-method-POST')
            importing_from_nexml_string = (import_method == 'import-method-NEXML' and nexml_pasted_string)
            importing_from_crossref_API = (import_method == 'import-method-PUBLICATION_DOI' and publication_doi_for_crossref) or \
                                          (import_method == 'import-method-PUBLICATION_REFERENCE' and publication_ref)

            # Are they using an existing license or waiver (CC0, CC-BY, something else?)
            using_existing_license = (kwargs.get('chosen_license', '') == 'study-data-has-existing-license')

            # any of these methods should returna parsed NexSON dict (vs. string)
            if importing_from_treebase_id:
                # make sure the treebase ID is an integer
                treebase_id = "".join(treebase_id.split())  # remove all whitespace
                treebase_id = treebase_id.lstrip('S').lstrip('s')  # allow for possible leading 'S'?
                try:
                    treebase_id = int(treebase_id)
                except ValueError, e:
                    raise HTTP(400, json.dumps({
                        "error": 1,
                        "description": "TreeBASE ID should be a simple integer, not '%s'! Details:\n%s" % (treebase_id, e.message)
                    }))
                try:
                    new_study_nexson = import_nexson_from_treebase(treebase_id, nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
                except Exception as e:
                    raise HTTP(500, json.dumps({
                        "error": 1,
                        "description": "Unexpected error parsing the file obtained from TreeBASE. Please report this bug to the Open Tree of Life developers."
                    }))
            # elif importing_from_nexml_fetch:
            #     if not (nexml_fetch_url.startswith('http://') or nexml_fetch_url.startswith('https://')):
            #         raise HTTP(400, json.dumps({
            #             "error": 1,
            #             "description": 'Expecting: "nexml_fetch_url" to startwith http:// or https://',
            #         }))
            #     new_study_nexson = get_ot_study_info_from_treebase_nexml(src=nexml_fetch_url,
            #                                                     nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
            # elif importing_from_nexml_string:
            #     new_study_nexson = get_ot_study_info_from_treebase_nexml(nexml_content=nexml_pasted_string,
            #                                                    nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
            elif importing_from_crossref_API:
                new_study_nexson = _new_nexson_with_crossref_metadata(doi=publication_doi_for_crossref, ref_string=publication_ref, include_cc0=cc0_agreement)
            elif importing_from_post_arg:
                bundle = __extract_and_validate_nexson(request,
                                                       repo_nexml2json,
                                                       kwargs)
                new_study_nexson = bundle[0]
            else:   # assumes 'import-method-MANUAL_ENTRY', or insufficient args above
                new_study_nexson = get_empty_nexson(BY_ID_HONEY_BADGERFISH, include_cc0=cc0_agreement)
                if publication_doi:
                    # submitter entered an invalid DOI (or other URL); add it now
                    new_study_nexson['nexml'][u'^ot:studyPublication'] = {'@href': publication_doi}

            nexml = new_study_nexson['nexml']

            if not importing_from_post_arg:
                # If submitter requested the CC0 waiver or other waiver/license, make sure it's here
                if cc0_agreement:
                    nexml['^xhtml:license'] = {'@href': 'http://creativecommons.org/publicdomain/zero/1.0/'}
                elif using_existing_license:
                    existing_license = kwargs.get('alternate_license', '')
                    if existing_license == 'CC-0':
                        nexml['^xhtml:license'] = {'@name': 'CC0', '@href': 'http://creativecommons.org/publicdomain/zero/1.0/'}
                        pass
                    elif existing_license == 'CC-BY-2.0':
                        nexml['^xhtml:license'] = {'@name': 'CC-BY 2.0', '@href': 'http://creativecommons.org/licenses/by/2.0/'}
                        pass
                    elif existing_license == 'CC-BY-2.5':
                        nexml['^xhtml:license'] = {'@name': 'CC-BY 2.5', '@href': 'http://creativecommons.org/licenses/by/2.5/'}
                        pass
                    elif existing_license == 'CC-BY-3.0':
                        nexml['^xhtml:license'] = {'@name': 'CC-BY 3.0', '@href': 'http://creativecommons.org/licenses/by/3.0/'}
                        pass
                    # NOTE that we don't offer CC-BY 4.0, which is problematic for data
                    elif existing_license == 'CC-BY':
                        # default to version 3, if not specified. 
                        nexml['^xhtml:license'] = {'@name': 'CC-BY 3.0', '@href': 'http://creativecommons.org/licenses/by/3.0/'}
                        pass
                    else:  # assume it's something else
                        alt_license_name = kwargs.get('alt_license_name', '')
                        alt_license_url = kwargs.get('alt_license_URL', '')
                        # OK to add a name here? mainly to capture submitter's intent
                        nexml['^xhtml:license'] = {'@name': alt_license_name, '@href': alt_license_url}

            nexml['^ot:curatorName'] = auth_info.get('name', '')

        phylesystem = api_utils.get_phylesystem(request)
        try:
            r = phylesystem.ingest_new_study(new_study_nexson,
                                             repo_nexml2json,
                                             auth_info,
                                             new_study_id)
            new_resource_id, commit_return = r
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())
        if commit_return['error'] != 0:
            # _LOG.debug('ingest_new_study failed with error code')
            raise HTTP(400, json.dumps(commit_return))
        __deferred_push_to_gh_call(request, new_resource_id, doc_type='nexson', **kwargs)
        return commit_return

    def __coerce_nexson_format(nexson, dest_format, current_format=None):
        '''Calls convert_nexson_format but does the appropriate logging and HTTP exceptions.
        '''
        try:
            return convert_nexson_format(nexson, dest_format, current_format=current_format)
        except:
            msg = "Exception in coercing to the required NexSON version for validation!"
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            # _LOG.exception(msg)
            raise HTTP(400, msg)

    def __extract_nexson_from_http_call(request, **kwargs):
        """Returns the nexson blob from `kwargs` or the request.body"""
        try:
            # check for kwarg 'nexson', or load the full request body
            if 'nexson' in kwargs:
                nexson = kwargs.get('nexson', {})
            else:
                nexson = request.body.read()

            if not isinstance(nexson, dict):
                nexson = json.loads(nexson)
            if 'nexson' in nexson:
                nexson = nexson['nexson']
        except:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            # _LOG.exception('Exception getting nexson content in __extract_nexson_from_http_call')
            raise HTTP(400, json.dumps({"error": 1, "description": 'NexSON must be valid JSON'}))
        return nexson

    def __extract_and_validate_nexson(request, repo_nexml2json, kwargs):
        try:
            nexson = __extract_nexson_from_http_call(request, **kwargs)
        #    from peyotl.manip import count_num_trees
        #    numtrees=count_num_trees(nexson,repo_nexml2json)
        #    _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        #    _LOG.debug('number of trees in nexson is {}, max number of trees is {}'.format(numtrees,max_num_trees))
            bundle = validate_and_convert_nexson(nexson,
                                                 repo_nexml2json,
                                                 allow_invalid=False,
                                                 max_num_trees_per_study=max_num_trees)
            nexson, annotation, validation_log, nexson_adaptor = bundle
        except GitWorkflowError, err:
            # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            # _LOG.exception('PUT failed in validation')
            _raise_HTTP_from_msg(err.msg or 'No message found')
        return nexson, annotation, nexson_adaptor

    def __make_valid_DOI(candidate):
        # Try to convert the candidate string to a proper, minimal DOI. Return the DOI,
        # or None if conversion is not possible.
        #   WORKS: http://dx.doi.org/10.999...
        #   WORKS: 10.999...
        #   FAILS: 11.999...
        #   WORKS: doi:10.999...
        #   WORKS: DOI:10.999...
        #   FAILS: http://example.com/
        #   WORKS: http://example.com/10.blah
        #   FAILS: something-else
        doi_prefix = '10.'
        # All existing DOIs use the directory indicator '10.', see
        #   http://www.doi.org/doi_handbook/2_Numbering.html#2.2.2

        # Remove all whitespace from the candidate string
        if not candidate:
            return None
        candidate = "".join(candidate.split())
        if doi_prefix in candidate:
            # Strip everything up to the first '10.'
            doi_parts = candidate.split(doi_prefix)
            doi_parts[0] = ''
            # Remove any preamble and return the minimal DOI
            return doi_prefix.join(doi_parts)
        else:
            return None

    def PUT(resource, resource_id=None, *args, **kwargs):
        "Open Tree API methods relating to updating existing resources"
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1.PUT')
        delegate = _route_tag2func.get(resource)
        if delegate:
            return delegate(**kwargs)
        #global TIMING
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study':
            # _LOG.debug('resource must be "study"')
            raise HTTP(400, 'resource != study')
        if resource_id is None:
            # _LOG.debug('resource id not provided')
            raise HTTP(400, json.dumps({"error": 1, "description": 'study ID expected after "study/"'}))
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        try:
            commit_msg = kwargs.get('commit_msg','')
            if commit_msg.strip() == '':
                # git rejects empty commit messages
                commit_msg = None
        except:
            commit_msg = None
        master_file_blob_included = kwargs.get('merged_SHA')
        # _LOG.debug('PUT to study {} for starting_commit_SHA = {} and merged_SHA = {}'.format(resource_id,
        #                                                                                     parent_sha,
        #                                                                                    str(master_file_blob_included)))
        #TIMING = api_utils.log_time_diff(_LOG)
        auth_info = api_utils.authenticate(**kwargs)
        #TIMING = api_utils.log_time_diff(_LOG, 'github authentication', TIMING)
        
        bundle = __extract_and_validate_nexson(request,
                                               repo_nexml2json,
                                               kwargs)
        nexson, annotation, nexson_adaptor = bundle

        #TIMING = api_utils.log_time_diff(_LOG, 'validation and normalization', TIMING)
        phylesystem = api_utils.get_phylesystem(request)
        try:
            gd = phylesystem.create_git_action(resource_id)
        except KeyError, err:
            # _LOG.debug('PUT failed in create_git_action (probably a bad study ID)')
            _raise_HTTP_from_msg("invalid study ID, please check the URL")
        try:
            blob = __finish_write_verb(phylesystem,
                                       gd,
                                       nexson=nexson,
                                       resource_id=resource_id,
                                       auth_info=auth_info,
                                       adaptor=nexson_adaptor,
                                       annotation=annotation,
                                       parent_sha=parent_sha, 
                                       commit_msg=commit_msg,
                                       master_file_blob_included=master_file_blob_included)
        except GitWorkflowError, err:
            # _LOG.exception('PUT failed in __finish_write_verb')
            _raise_HTTP_from_msg(err.msg)
        #TIMING = api_utils.log_time_diff(_LOG, 'blob creation', TIMING)
        mn = blob.get('merge_needed')
        if (mn is not None) and (not mn):
            __deferred_push_to_gh_call(request, resource_id, doc_type='nexson', **kwargs)
        # Add updated commit history to the blob
        blob['versionHistory'] = phylesystem.get_version_history_for_study_id(resource_id)
        return blob

    def _new_nexson_with_crossref_metadata(doi, ref_string, include_cc0=False):
        # look for matching studies via CrossRef.org API
        # N.B. The recommended API method is very different for DOI vs.
        # a reference string, but we can also use the filter option to get
        # consistent behavior and response.
        best_match = None
        no_match_found = False
        meta_publication_reference = u''
        try:
            if doi:
                # use the supplied DOI to fetch study metadata
                lookup_response = fetch(
                    'https://api.crossref.org/works?%s' %
                    urlencode({'rows': 1, 'filter': 'doi:'+ doi})
                )
            elif ref_string:
                # use the supplied reference text to fetch study metadata
                lookup_response = fetch(
                    'https://api.crossref.org/works?%s' %
                    urlencode({'rows': 1, 'query': ref_string})
                )
            lookup_response = unicode(lookup_response, 'utf-8')   # make sure it's Unicode!
            response_json = anyjson.loads(lookup_response)
            response_status = response_json.get('status', u'')
            if response_status == u'ok':
                matching_records = response_json.get('message', {}).get('items', [])
                if len(matching_records) == 0:
                    no_match_found = True
            else:
                # Something went wrong (TODO: Capture and log any error message?)
                no_match_found = True

        except urllib2.URLError, e:
            # Both calls above should return a 200 status even if there's no match.
            # So apparently the CrossRef service is down for some reason.
            no_match_found = True

        if no_match_found:
            # Add a bogus reference string to signal the lack of results
            meta_publication_url = u''
            meta_year = u''
            if doi:
                meta_publication_reference = u'No matching publication found for this DOI!'
            else:
                meta_publication_reference = u'No matching publication found for this reference string'
        else:
            # We got a match! These are sorted by score, so we should assume the
            # first (possibly only) record is the best match.
            # See https://github.com/CrossRef/rest-api-doc#sort-order
            match = matching_records[0];
            meta_publication_url = match.get('URL', u'')  # should be its DOI in URL form
            # Try to capture the publication year (print first, or online)
            meta_year = u''
            date_parts = match.get('published-print', {}).get('date-parts', [])
            if len(date_parts) == 0:
                # try again using online publication
                date_parts = match.get('published-online', {}).get('date-parts', [])
            if len(date_parts) > 0:
                # retrieve its inner parts list (not sure why this is nested)
                inner_date_parts = date_parts[0];
                if len(inner_date_parts) > 0:
                    # first/only element here should be a year
                    meta_year = inner_date_parts[0]

            # capture the raw DOI so we can try to retrieve a reference string below
            doi = match.get('DOI', u'')

        # We need another API call to fetch a plain-text reference string.
        # NB - this is probabl APA style (based on conversation with CrossRef API team)
        if doi:
            try:
                # use the supplied (or recovered) DOI to fetch a plain-text reference string
                lookup_response = fetch(
                    'https://api.crossref.org/works/%s/transform/text/x-bibliography' %
                    quote_plus(doi)
                )
                # make sure it's Unicode!
                raw_publication_reference = unicode(lookup_response, 'utf-8')
                # make sure it's plain text (no markup)!
                ref_element_tree = web2pyHTMLParser(raw_publication_reference).tree
                # root of this tree is the complete mini-DOM
                ref_root = ref_element_tree.elements()[0]
                # reduce this root to plain text (strip any tags)
                meta_publication_reference = ref_root.flatten()

            except urllib2.URLError, e:
                # Any response but 200 means no match found, or the CrossRef
                # service is down for some reason.
                _GLOG.debug("URLError fetching ref-text!!")
                _GLOG.debug(e)
                meta_publication_reference = u'No matching publication found for this DOI!'

        # add any found values to a fresh NexSON template
        nexson = get_empty_nexson(BY_ID_HONEY_BADGERFISH, include_cc0=include_cc0)
        nexml_el = nexson['nexml']
        nexml_el[u'^ot:studyPublicationReference'] = meta_publication_reference
        if meta_publication_url:
            nexml_el[u'^ot:studyPublication'] = {'@href': meta_publication_url}
        if meta_year:
            nexml_el[u'^ot:studyYear'] = meta_year
        return nexson

    def DELETE(resource, resource_id=None, *args, **kwargs):
        "Open Tree API methods relating to deleting existing resources"
        if not check_not_read_only():
            raise HTTP(500, "should raise from check_not_read_only")
        delegate = _route_tag2func.get(resource)
        if delegate:
            return delegate(**kwargs)
        # support JSONP request from another domain
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1.DELETE')
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study':
            raise HTTP(400, 'resource != study')
        if resource_id is None:
            # _LOG.debug('resource id not provided')
            raise HTTP(400, json.dumps({"error": 1, "description": 'study ID expected after "study/"'}))
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        try:
            commit_msg = kwargs.get('commit_msg','')
            if commit_msg.strip() == '':
                # git rejects empty commit messages
                commit_msg = None
        except:
            commit_msg = None
        auth_info = api_utils.authenticate(**kwargs)
        phylesystem = api_utils.get_phylesystem(request)
        try:
            x = phylesystem.delete_study(resource_id, auth_info, parent_sha, commit_msg=commit_msg)
            if x.get('error') == 0:
                __deferred_push_to_gh_call(request, None, doc_type='nexson', **kwargs)
            return x
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            # _LOG.exception('Exception getting nexson content in phylesystem.delete_study')
            raise HTTP(400, json.dumps({"error": 1, "description": 'Unknown error in study deletion'}))

    def OPTIONS(*args, **kwargs):
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, **(response.headers))

    return locals()
