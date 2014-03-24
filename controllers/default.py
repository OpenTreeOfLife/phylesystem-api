import os, sys
import time
import json
import anyjson
import hashlib
import github
import traceback
from sh import git
from peyotl import can_convert_nexson_forms, convert_nexson_format
from peyotl.phylesystem.git_workflows import acquire_lock_raise, \
                                             commit_and_try_merge2master, \
                                             delete_study, \
                                             GitWorkflowError, \
                                             validate_and_convert_nexson
from peyotl.nexson_syntax import get_empty_nexson, \
                                 get_ot_study_info_from_nexml, \
                                 BY_ID_HONEY_BADGERFISH
from peyotl.external import import_nexson_from_treebase
from github import Github, BadCredentialsException
import api_utils
from pprint import pprint
from gitdata import GitData
from gluon.tools import fetch
from urllib import urlencode
from gluon.html import web2pyHTMLParser
from StringIO import StringIO

_VALIDATING = True
_LOG = api_utils.get_logger('ot_api.default')

def _raise_HTTP_from_msg(msg):
    raise HTTP(400, json.dumps({"error": 1, "description": msg}))

def _acquire_lock_raise_http(gd):
    try:
        acquire_lock_raise(gd)
    except GitWorkflowError, err:
        _raise_HTTP_from_msg(err.msg)

def index():
    response.view = 'generic.json'
    return json.dumps({
        "description": "The Open Tree API",
        "source_url": "https://github.com/OpenTreeOfLife/api.opentreeoflife.org/",
        "documentation_url": "https://github.com/OpenTreeOfLife/api.opentreeoflife.org/tree/master/docs"
    })

_CONFIG_TUPLE = None
def reponexsonformat():
    global _CONFIG_TUPLE
    response.view = 'generic.jsonp'
    if _CONFIG_TUPLE is None:
        _CONFIG_TUPLE = api_utils.read_config(request)
    rn = _CONFIG_TUPLE[4]
    return {'description': "The nexml2json property reports the version of the NexSON that is used in the document store. Using other forms of NexSON with the API is allowed, but may be slower.",
            'nexml2json': rn}

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = 86400  # cache for a day

    repo_path, repo_remote, git_ssh, pkey, repo_nexml2json = api_utils.read_config(request)

    def __validate_output_nexml2json(kwargs):
        output_nexml2json = kwargs.get('output_nexml2json', '0.0.0')
        if (output_nexml2json != repo_nexml2json) and not can_convert_nexson_forms(repo_nexml2json, output_nexml2json):
            msg = 'Cannot convert from {s} to {d}'.format(s=repo_nexml2json, d=output_nexml2json)
            _LOG.debug('GET failing: {m}'.format(m=msg))
            raise HTTP(400, json.dumps({"error": 1, "description": msg}))
        return output_nexml2json

    def __finish_write_verb(git_data, 
                            nexson,
                            resource_id,
                            auth_info,
                            adaptor,
                            annotation,
                            parent_sha,
                            master_file_blob_included=None):
        '''Called by PUT and POST handlers to avoid code repetition.'''
        # global TIMING
        #TODO, need to make this spawn a thread to do the second commit rather than block
#        adaptor.add_or_replace_annotation(nexson,
#                                          annotation['annotationEvent'],
#                                          annotation['agent'])
        annotated_commit = commit_and_try_merge2master(git_data,
                                                       nexson,
                                                       resource_id,
                                                       auth_info,
                                                       parent_sha,
                                                       master_file_blob_included)
        # TIMING = api_utils.log_time_diff(_LOG, 'annotated commit', TIMING)
        if annotated_commit['error'] != 0:
            _LOG.debug('annotated_commit failed')
            raise HTTP(400, json.dumps(annotated_commit))
        return annotated_commit

    def GET(resource,resource_id,jsoncallback=None,callback=None,_=None,**kwargs):
        "OpenTree API methods relating to reading"
        valid_resources = ('study', )
        output_nexml2json = __validate_output_nexml2json(kwargs)
        if resource not in valid_resources:
            raise HTTP(400, json.dumps({"error": 1,
                "description": 'Resource requested not in list of valid resources: %s' % valid_resources }))

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        # return the correct nexson of study_id, using the specified view
        gd = GitData(repo=repo_path, remote=repo_remote, git_ssh=git_ssh, pkey=pkey)
        _acquire_lock_raise_http(gd)
        try:
            r = gd.return_study(resource_id, return_WIP_map=True)
            #_LOG.debug('return_study responded with "{}"'.format(str(r)))
            study_nexson, head_sha, wip_map = r
        finally:
            gd.release_lock()
        if study_nexson == "":
            raise HTTP(404, json.dumps({"error": 1, "description": 'Study #%s was not found' % resource_id}))
        
        study_nexson = anyjson.loads(study_nexson)
        if output_nexml2json != repo_nexml2json:
            study_nexson = __coerce_nexson_format(study_nexson,
                                          output_nexml2json,
                                          current_format=repo_nexml2json)
        return {'sha': head_sha,
                'data': study_nexson,
                'branch2sha': wip_map
                }

    def POST(resource, resource_id=None, _method='POST', **kwargs):
        "Open Tree API methods relating to creating (and importing) resources"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        
        # check for HTTP method override (passed on query string)
        if _method == 'PUT':
            PUT(resource, resource_id, kwargs)
        elif _method == 'DELETE':
            DELETE(resource, resource_id, kwargs)
        # elif _method == 'PATCH': ...

        if not resource=='study':
            raise HTTP(400, json.dumps({"error":1,
                                        "description": "Only the creation of new studies is currently supported"}))
        
        # we're creating a new study (possibly with import instructions in the payload)
        cc0_agreement = kwargs.get('cc0_agreement', '')
        import_option = kwargs.get('import_option', '')
        treebase_id = kwargs.get('treebase_id', '')
        nexml_fetch_url = kwargs.get('nexml_fetch_url', '')
        nexml_pasted_string = kwargs.get('nexml_pasted_string', '')
        publication_doi = kwargs.get('publication_DOI', '')
        publication_ref = kwargs.get('publication_reference', '')
        ##dryad_DOI = kwargs.get('dryad_DOI', '')

        # check for required license agreement!
        if cc0_agreement != 'true':
            d = {"error":1,
                 "description": "CC-0 license must be accepted to add studies using this API."}
            raise HTTP(400, json.dumps(d))

        auth_info = api_utils.authenticate(**kwargs)

        app_name = "api"
        # add known values for its metatags
        meta_publication_reference = None

        # create initial study NexSON using the chosen import option
        importing_from_treebase_id = (import_option == 'IMPORT_FROM_TREEBASE' and treebase_id)
        importing_from_nexml_fetch = (import_option == 'IMPORT_FROM_NEXML' and nexml_fetch_url)
        importing_from_nexml_string = (import_option == 'IMPORT_FROM_NEXML' and nexml_pasted_string)
        #importing_from_nexml_upload = (import_option == 'IMPORT_FROM_NEXML' and publication_doi)
        #importing_from_nexml = (importing_from_treebase_id or importing_from_nexml_fetch or importing_from_nexml_string)  # or importing_from_nexml_upload

        importing_from_crossref_API = (import_option == 'IMPORT_FROM_PUBLICATION_DOI' and publication_doi) or \
                                      (import_option == 'IMPORT_FROM_PUBLICATION_REFERENCE' and publication_ref)

        # any of these methods should returna parsed NexSON dict (vs. string)
        if importing_from_treebase_id:
            # make sure the treebase ID is an integer
            treebase_id = "".join(treebase_id.split())  # remove all whitespace
            treebase_id = treebase_id.lstrip('S').lstrip('s')  # allow for possible leading 'S'?
            try:
                treebase_id = int(treebase_id)
            except ValueError:
                raise HTTP(400, json.dumps({
                    "error": 1,
                    "description": "TreeBASE ID should be a simple integer, not '%s'! Details:\n%s" % (treebase_id, e.message)
                }))
            new_study_nexson = import_nexson_from_treebase(treebase_id, nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
        elif importing_from_nexml_fetch:
            if not (nexml_fetch_url.startswith('http://') or nexml_fetch_url.startswith('https://')):
                raise HTTP(400, json.dumps({
                    "error": 1,
                    "description": 'Expecting: "nexml_fetch_url" to startwith http:// or https://',
                }))
            new_study_nexson = get_ot_study_info_from_nexml(fetch_url=nexml_fetch_url,
                                                            nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
        elif importing_from_nexml_string:
            new_study_nexson = get_ot_study_info_from_nexml(nexml_content=nexml_pasted_string,
                                                            nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
        elif importing_from_crossref_API:
            new_study_nexson = _new_nexson_with_crossref_metadata(doi=publication_doi, ref_string=publication_ref)
        else:   # assumes IMPORT_FROM_MANUAL_ENTRY, or insufficient args above
            new_study_nexson = get_empty_nexson(BY_ID_HONEY_BADGERFISH)

        gd = GitData(repo=repo_path, remote=repo_remote, git_ssh=git_ssh, pkey=pkey)
        # studies created by the OpenTree API start with o,
        # so they don't conflict with new study id's from other sources
        new_resource_id = "o%d" % (gd.newest_study_id() + 1)
        nexml = new_study_nexson['nexml']
        nexml['^ot:studyId'] = new_resource_id
        nexml['^ot:curatorName'] = auth_info.get('name', '').decode('utf-8')
        kwargs['nexson'] = new_study_nexson
        try:
            bundle = validate_and_convert_nexson(new_study_nexson, repo_nexml2json, allow_invalid=True)
            nexson, annotation, validation_log, nexson_adaptor = bundle
            commit_return = __finish_write_verb(gd,
                                         nexson,
                                         new_resource_id,
                                         auth_info,
                                         nexson_adaptor,
                                         annotation,
                                         parent_sha=None)
            return commit_return
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            raise HTTP(400, traceback.format_exc())

    def __coerce_nexson_format(nexson, dest_format, current_format=None):
        '''Calls convert_nexson_format but does the appropriate logging and HTTP exceptions.
        '''
        try:
            return convert_nexson_format(nexson, dest_format, current_format=current_format)
        except:
            msg = "Exception in coercing to the required NexSON version for validation. "
            _LOG.exception(msg)
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
            _LOG.exception('Exception getting nexson content in __extract_nexson_from_http_call')
            raise HTTP(400, json.dumps({"error": 1, "description": 'NexSON must be valid JSON'}))
        return nexson

    def PUT(resource, resource_id, **kwargs):
        "Open Tree API methods relating to updating existing resources"
        #global TIMING
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study':
            _LOG.debug('resource must be "study"')
            raise HTTP(400, 'resource != study')
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        master_file_blob_included = kwargs.get('merged_SHA')
        #TIMING = api_utils.log_time_diff(_LOG)
        auth_info = api_utils.authenticate(**kwargs)
        #TIMING = api_utils.log_time_diff(_LOG, 'github authentication', TIMING)
        
        try:
            nexson = __extract_nexson_from_http_call(request, **kwargs)
            bundle = validate_and_convert_nexson(nexson, repo_nexml2json, allow_invalid=False)
            nexson, annotation, validation_log, nexson_adaptor = bundle
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)

        #TIMING = api_utils.log_time_diff(_LOG, 'validation and normalization', TIMING)
        gd = GitData(repo=repo_path, remote=repo_remote, git_ssh=git_ssh, pkey=pkey)
        try:
            blob = __finish_write_verb(gd,
                                   nexson,
                                   resource_id,
                                   auth_info,
                                   nexson_adaptor,
                                   annotation,
                                   parent_sha,
                                   master_file_blob_included)
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        #TIMING = api_utils.log_time_diff(_LOG, 'blob creation', TIMING)
        return blob

    def _new_nexson_with_crossref_metadata(doi, ref_string):
        if doi:
            # use the supplied DOI to fetch study metadata

            # Cleanup submitted DOI to work with CrossRef API.
            #   WORKS: http://dx.doi.org/10.999...
            #   WORKS: doi:10.999...
            #   FAILS: doi: 10.999...
            #   FAILS: DOI:10.999...
            # Let's keep it simple and make it a bare DOI.
            # All DOIs use the directory indicator '10.', see
            #   http://www.doi.org/doi_handbook/2_Numbering.html#2.2.2

            # Remove all whitespace from the submitted DOI...
            publication_doi = "".join(doi.split())
            # ... then strip everything up to the first '10.'
            doi_parts = publication_doi.split('10.')
            doi_parts[0] = ''
            search_term = '10.'.join(doi_parts)

        elif ref_string:
            # use the supplied reference text to fetch study metadata
            search_term = ref_string

        # look for matching studies via CrossRef.org API
        doi_lookup_response = fetch(
            'http://search.crossref.org/dois?%s' % 
            urlencode({'q': search_term})
        )
        doi_lookup_response = unicode(doi_lookup_response, 'utf-8')   # make sure it's Unicode!
        matching_records = anyjson.loads(doi_lookup_response)

        # if we got a match, grab the first (probably only) record
        if len(matching_records) > 0:
            match = matching_records[0];

            # Convert HTML reference string to plain text
            raw_publication_reference = match.get('fullCitation', '')
            ref_element_tree = web2pyHTMLParser(raw_publication_reference).tree
            # root of this tree is the complete mini-DOM
            ref_root = ref_element_tree.elements()[0]
            # reduce this root to plain text (strip any tags)

            meta_publication_reference = ref_root.flatten().decode('utf-8')
            meta_publication_url = match.get('doi', u'')  # already in URL form
            meta_year = match.get('year', u'')
            
        else:
            # Add a bogus reference string to signal the lack of results
            if doi:
                meta_publication_reference = u'No matching publication found for this DOI!'
            else:
                meta_publication_reference = u'No matching publication found for this reference string'
            meta_publication_url = u''
            meta_year = u''

        # add any found values to a fresh NexSON template
        nexson = get_empty_nexson(BY_ID_HONEY_BADGERFISH)
        nexml_el = nexson['nexml']
        nexml_el[u'^ot:studyPublicationReference'] = meta_publication_reference
        if meta_publication_url:
            nexml_el[u'^ot:studyPublication'] = {'@href': meta_publication_url}
        if meta_year:
            nexml_el[u'^ot:studyYear'] = meta_year
        return nexson

    def do_commit(gd, gh, file_content, author_name, author_email, resource_id):
        """Actually make a local Git commit and push it to our remote
        """
        # global TIMING
        author  = "%s <%s>" % (author_name, author_email)

        branch_name  = "%s_study_%s" % (gh.get_user().login, resource_id)

        _acquire_lock_or_exit(gd, fail_msg="Could not acquire lock to write to study #{s}".format(s=resource_id))
        try:
            gd.checkout_master()
            _pull_gh(gd, repo_remote, "master", resource_id)
            
            try:
                new_sha = gd.write_study(resource_id, file_content, branch_name,author)
                # TIMING = api_utils.log_time_diff(_LOG, 'writing study', TIMING)
            except Exception, e:
                raise HTTP(400, json.dumps({
                    "error": 1,
                    "description": "Could not write to study #%s ! Details: \n%s" % (resource_id, e.message)
                }))
            gd.merge(branch_name)
            _push_gh(gd, repo_remote, "master", resource_id)
        finally:
            gd.release_lock()

        # What other useful information should be returned on a successful write?
        return {
            "error": 0,
            "resource_id": resource_id,
            "branch_name": branch_name,
            "description": "Updated study #%s" % resource_id,
            "sha":  new_sha
        }

    def DELETE(resource, resource_id=None, **kwargs):
        "Open Tree API methods relating to deleting existing resources"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study':
            raise HTTP(400, 'resource != study')
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        auth_info = api_utils.authenticate(**kwargs)
        gd = GitData(repo=repo_path, remote=repo_remote, git_ssh=git_ssh, pkey=pkey)
        return delete_study(gd, resource_id, auth_info, parent_sha)

    def OPTIONS(*args, **kwargs):
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, **(response.headers))

    return locals()
