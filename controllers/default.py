import os, sys
import time
import json
import anyjson
import hashlib
import github
import traceback
from sh import git
from peyotl import can_convert_nexson_forms, convert_nexson_format
from peyotl.phylesystem.git_workflows import GitWorkflowError, \
                                             validate_and_convert_nexson
from peyotl.nexson_syntax import get_empty_nexson, \
                                 get_ot_study_info_from_nexml, \
                                 BY_ID_HONEY_BADGERFISH
from peyotl.external import import_nexson_from_treebase
from github import Github, BadCredentialsException
import api_utils
from pprint import pprint
from gluon.tools import fetch
from urllib import urlencode
from gluon.html import web2pyHTMLParser
from StringIO import StringIO
import copy
_GLOG = api_utils.get_logger(None, 'ot_api.default.global')
try:
    from open_tree_tasks import call_http_json
    _GLOG.debug('call_http_json imported')
except:
    call_http_json = None
    _GLOG.debug('call_http_json was not imported from open_tree_tasks')



_VALIDATING = True

def _raise_HTTP_from_msg(msg):
    raise HTTP(400, json.dumps({"error": 1, "description": msg}))

def __deferred_push_to_gh_call(request, resource_id, **kwargs):
    _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    _LOG.debug('in __deferred_push_to_gh_call')
    if call_http_json is not None:
        url = api_utils.compose_push_to_github_url(request, resource_id)
        auth_token = copy.copy(kwargs.get('auth_token'))
        data = {}
        if auth_token is not None:
            data['auth_token'] = auth_token
        _LOG.debug('__deferred_push_to_gh_call({u}, {d})'.format(u=url, d=str(data)))
        call_http_json.delay(url=url, verb='PUT', data=data)
        

def index():
    response.view = 'generic.json'
    return json.dumps({
        "description": "The Open Tree API",
        "source_url": "https://github.com/OpenTreeOfLife/phylesystem-api/",
        "documentation_url": "https://github.com/OpenTreeOfLife/phylesystem-api/tree/master/docs"
    })

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
    except:
        raise HTTP(400, '{"error": 1, "description": "Expecting study_id as the argument"}')
    phylesystem = api_utils.get_phylesystem(request)
    try:
        u = phylesystem.get_public_url(study_id)
        return json.dumps({'url': u, 'study_id': study_id})
    except:
        _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        _LOG.exception('study {} not found in external_url'.format(study_id))
        raise HTTP(404, '{"error": 1, "description": "study not found"}')

def reponexsonformat():
    response.view = 'generic.jsonp'
    phylesystem = api_utils.get_phylesystem(request)
    return {'description': "The nexml2json property reports the version of the NexSON that is used in the document store. Using other forms of NexSON with the API is allowed, but may be slower.",
            'nexml2json': phylesystem.repo_nexml2json}

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = 86400  # cache for a day


    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json

    def __validate_output_nexml2json(kwargs):
        output_nexml2json = kwargs.get('output_nexml2json', '0.0.0')
        if (output_nexml2json != repo_nexml2json) and not can_convert_nexson_forms(repo_nexml2json, output_nexml2json):
            msg = 'Cannot convert from {s} to {d}'.format(s=repo_nexml2json, d=output_nexml2json)
            _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            _LOG.debug('GET failing: {m}'.format(m=msg))
            raise HTTP(400, json.dumps({"error": 1, "description": msg}))
        return output_nexml2json

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

    def GET(resource, resource_id, jsoncallback=None, callback=None, _=None, **kwargs):
        "OpenTree API methods relating to reading"
        _LOG = api_utils.get_logger(request, 'ot_api.default.v1.GET')
        valid_resources = ('study', )
        _LOG.debug('GET default/v1/study/{}'.format(str(resource_id)))
        output_nexml2json = __validate_output_nexml2json(kwargs)
        if resource not in valid_resources:
            raise HTTP(400, json.dumps({"error": 1,
                "description": 'Resource requested not in list of valid resources: %s' % valid_resources }))

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'
        parent_sha = kwargs.get('starting_commit_SHA')
        _LOG.debug('parent_sha = {}'.format(parent_sha))
        # return the correct nexson of study_id, using the specified view
        phylesystem = api_utils.get_phylesystem(request)
        try:
           r = phylesystem.return_study(resource_id, commit_sha=parent_sha, return_WIP_map=True)
        except:
            _LOG.exception('GET failed')
            raise HTTP(404, json.dumps({"error": 1, "description": 'Study #%s GET failure' % resource_id}))
        try:
           study_nexson, head_sha, wip_map = r
           blob_sha = phylesystem.get_blob_sha_for_study_id(resource_id, head_sha)
           phylesystem.add_validation_annotation(study_nexson, blob_sha)
           version_history = phylesystem.get_version_history_for_study_id(resource_id)
           if output_nexml2json != repo_nexml2json:
                study_nexson = __coerce_nexson_format(study_nexson,
                                          output_nexml2json,
                                          current_format=repo_nexml2json)
        except:
            _LOG.exception('GET failed')
            e = sys.exc_info()[0]
            _raise_HTTP_from_msg(e)
        #Apply the annotations
        #create phylesystem action to get blob sha for a file given HEAD and study_ID
        return {'sha': head_sha,
                'data': study_nexson,
                'versionHistory': version_history,
                'branch2sha': wip_map
                }

    def POST(resource, resource_id=None, _method='POST', **kwargs):
        "Open Tree API methods relating to creating (and importing) resources"
        _LOG = api_utils.get_logger(request, 'ot_api.default.v1.POST')
        
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        # check for HTTP method override (passed on query string)
        if _method == 'PUT':
            PUT(resource, resource_id, kwargs)
        elif _method == 'DELETE':
            DELETE(resource, resource_id, kwargs)
        if not resource=='study':
            raise HTTP(400, json.dumps({"error":1,
                                        "description": "Only the creation of new studies is currently supported"}))
        auth_info = api_utils.authenticate(**kwargs)
        # Studies that were created in phylografter, can be added by
        #   POSTing the content with resource_id 
        new_study_id = resource_id
        if new_study_id is not None:
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
            publication_ref = kwargs.get('publication_reference', '')
            # is the submitter explicity applying the CC0 waiver to a new study
            # (i.e., this study is not currently in an online repository)?
            if import_from_location == 'IMPORT_FROM_UPLOAD':
                cc0_agreement = (kwargs.get('chosen_license', '') == 'apply-new-CC0-waiver' and 
                                 kwargs.get('cc0_agreement', '') == 'true')
            else:
                cc0_agreement = False
            # look for the chosen import method, e.g,
            # 'import-method-PUBLICATION_DOI' or 'import-method-MANUAL_ENTRY'
            import_method = kwargs.get('import_method', '')

            ##dryad_DOI = kwargs.get('dryad_DOI', '')

            app_name = "api"
            # add known values for its metatags
            meta_publication_reference = None

            # Create initial study NexSON using the chosen import method.
            #
            # N.B. We're currently using a streamlined creation path with just
            # two methods (TreeBASE ID and publication DOI). But let's keep the
            # logic for others, just in case we revert based on user feedback.
            importing_from_treebase_id = (import_method == 'import-method-TREEBASE_ID' and treebase_id)
            importing_from_nexml_fetch = (import_method == 'import-method-NEXML' and nexml_fetch_url)
            importing_from_nexml_string = (import_method == 'import-method-NEXML' and nexml_pasted_string)
            importing_from_crossref_API = (import_method == 'import-method-PUBLICATION_DOI' and publication_doi) or \
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
                new_study_nexson = import_nexson_from_treebase(treebase_id, nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
            # elif importing_from_nexml_fetch:
            #     if not (nexml_fetch_url.startswith('http://') or nexml_fetch_url.startswith('https://')):
            #         raise HTTP(400, json.dumps({
            #             "error": 1,
            #             "description": 'Expecting: "nexml_fetch_url" to startwith http:// or https://',
            #         }))
            #     new_study_nexson = get_ot_study_info_from_nexml(src=nexml_fetch_url,
            #                                                     nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
            # elif importing_from_nexml_string:
            #     new_study_nexson = get_ot_study_info_from_nexml(nexml_content=nexml_pasted_string,
            #                                                    nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
            elif importing_from_crossref_API:
                new_study_nexson = _new_nexson_with_crossref_metadata(doi=publication_doi, ref_string=publication_ref, include_cc0=cc0_agreement)
            else:   # assumes 'import-method-MANUAL_ENTRY', or insufficient args above
                new_study_nexson = get_empty_nexson(BY_ID_HONEY_BADGERFISH, include_cc0=cc0_agreement)

            nexml = new_study_nexson['nexml']

            # If submitter requested the CC0 waiver or other waiver/license, make sure it's here
            if importing_from_treebase_id or cc0_agreement:
                nexml['^xhtml:license'] = {'@href': 'http://creativecommons.org/publicdomain/zero/1.0/'}
            elif using_existing_license:
                existing_license = kwargs.get('alternate_license', '')
                if existing_license == 'CC-0':
                    nexml['^xhtml:license'] = {'@href': 'http://creativecommons.org/publicdomain/zero/1.0/'}
                    pass
                elif existing_license == 'CC-BY':
                    nexml['^xhtml:license'] = {'@href': 'http://creativecommons.org/licenses/by/4.0/'}
                    pass
                else:  # assume it's something else
                    alt_license_name = kwargs.get('alt_license_name', '')
                    alt_license_url = kwargs.get('alt_license_URL', '')
                    # OK to add a name here? mainly to capture submitter's intent
                    nexml['^xhtml:license'] = {'@name': alt_license_name, '@href': alt_license_url}

            nexml['^ot:curatorName'] = auth_info.get('name', '').decode('utf-8')

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
            _LOG.debug('ingest_new_study failed with error code')
            raise HTTP(400, json.dumps(commit_return))
        __deferred_push_to_gh_call(request, new_resource_id, **kwargs)
        return commit_return

    def __coerce_nexson_format(nexson, dest_format, current_format=None):
        '''Calls convert_nexson_format but does the appropriate logging and HTTP exceptions.
        '''
        try:
            return convert_nexson_format(nexson, dest_format, current_format=current_format)
        except:
            msg = "Exception in coercing to the required NexSON version for validation. "
            _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
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
            _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            _LOG.exception('Exception getting nexson content in __extract_nexson_from_http_call')
            raise HTTP(400, json.dumps({"error": 1, "description": 'NexSON must be valid JSON'}))
        return nexson

    def __extract_and_validate_nexson(request, repo_nexml2json, kwargs):
        try:
            nexson = __extract_nexson_from_http_call(request, **kwargs)
            bundle = validate_and_convert_nexson(nexson,
                                                 repo_nexml2json,
                                                 allow_invalid=True)
            nexson, annotation, validation_log, nexson_adaptor = bundle
        except GitWorkflowError, err:
            _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            _LOG.exception('PUT failed in validation')
            _raise_HTTP_from_msg(err.msg)
        return nexson, annotation, nexson_adaptor

    def PUT(resource, resource_id, **kwargs):
        "Open Tree API methods relating to updating existing resources"
        #global TIMING
        _LOG = api_utils.get_logger(request, 'ot_api.default.v1.PUT')
        
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study':
            _LOG.debug('resource must be "study"')
            raise HTTP(400, 'resource != study')
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        commit_msg = kwargs.get('commit_msg')
        master_file_blob_included = kwargs.get('merged_SHA')
        _LOG.debug('PUT to study {} for starting_commit_SHA = {} and merged_SHA = {}'.format(resource_id,
                                                                                             parent_sha,
                                                                                             str(master_file_blob_included)))
        #TIMING = api_utils.log_time_diff(_LOG)
        auth_info = api_utils.authenticate(**kwargs)
        #TIMING = api_utils.log_time_diff(_LOG, 'github authentication', TIMING)
        
        bundle = __extract_and_validate_nexson(request,
                                               repo_nexml2json,
                                               kwargs)
        nexson, annotation, nexson_adaptor = bundle

        #TIMING = api_utils.log_time_diff(_LOG, 'validation and normalization', TIMING)
        phylesystem = api_utils.get_phylesystem(request)
        gd = phylesystem.create_git_action(resource_id)
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
            _LOG.exception('PUT failed in __finish_write_verb')
            _raise_HTTP_from_msg(err.msg)
        #TIMING = api_utils.log_time_diff(_LOG, 'blob creation', TIMING)
        mn = blob.get('merge_needed')
        if (mn is not None) and (not mn):
            __deferred_push_to_gh_call(request, resource_id, **kwargs)
        return blob

    def _new_nexson_with_crossref_metadata(doi, ref_string, include_cc0=False):
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
        nexson = get_empty_nexson(BY_ID_HONEY_BADGERFISH, include_cc0=include_cc0)
        nexml_el = nexson['nexml']
        nexml_el[u'^ot:studyPublicationReference'] = meta_publication_reference
        if meta_publication_url:
            nexml_el[u'^ot:studyPublication'] = {'@href': meta_publication_url}
        if meta_year:
            nexml_el[u'^ot:studyYear'] = meta_year
        return nexson

    def DELETE(resource, resource_id=None, **kwargs):
        "Open Tree API methods relating to deleting existing resources"
        # support JSONP request from another domain
        _LOG = api_utils.get_logger(request, 'ot_api.default.v1.DELETE')
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study':
            raise HTTP(400, 'resource != study')
        parent_sha = kwargs.get('starting_commit_SHA')
        if parent_sha is None:
            raise HTTP(400, 'Expecting a "starting_commit_SHA" argument with the SHA of the parent')
        auth_info = api_utils.authenticate(**kwargs)
        phylesystem = api_utils.get_phylesystem(request)
        try:
            x = phylesystem.delete_study(resource_id, auth_info, parent_sha)
            if x.get('error') == 0:
                __deferred_push_to_gh_call(request, None, **kwargs)
            return x
        except GitWorkflowError, err:
            _raise_HTTP_from_msg(err.msg)
        except:
            _LOG.exception('Exception getting nexson content in phylesystem.delete_study')
            raise HTTP(400, json.dumps({"error": 1, "description": 'Unknown error in study deletion'}))

    def OPTIONS(*args, **kwargs):
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, **(response.headers))

    return locals()
