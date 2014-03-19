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
from peyotl.nexson_syntax import get_empty_nexson
from github import Github, BadCredentialsException
import api_utils
from pprint import pprint
from gitdata import GitData
from gluon.tools import fetch
from urllib import urlencode
from gluon.html import web2pyHTMLParser

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
        block_until_annotation_commit = True
        unadulterated_content_commit = commit_and_try_merge2master(git_data,
                                                                   nexson,
                                                                   resource_id,
                                                                   auth_info,
                                                                   parent_sha,
                                                                   master_file_blob_included)
        # TIMING = api_utils.log_time_diff(_LOG, 'unadulterated commit', TIMING)
        if unadulterated_content_commit['error'] != 0:
            _LOG.debug('unadulterated_content_commit failed')
            raise HTTP(400, json.dumps(unadulterated_content_commit))
        if _VALIDATING and block_until_annotation_commit:
            # add the annotation and commit the resulting blob...
            adaptor.add_or_replace_annotation(nexson,
                                              annotation['annotationEvent'],
                                              annotation['agent'])
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
        else:
            return unadulterated_content_commit

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
            study_nexson, head_sha = gd.return_study(resource_id)
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
                'data': study_nexson}

    def POST(resource, resource_id=None, _method='POST', **kwargs):
        "Open Tree API methods relating to creating (and importing) resources"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        output_nexml2json = __validate_output_nexml2json(kwargs)

        
        # check for HTTP method override (passed on query string)
        if _method == 'PUT':
            PUT(resource, resource_id, kwargs)
        elif _method == 'DELETE':
            DELETE(resource, resource_id, kwargs)
        # elif _method == 'PATCH': ...

        if not resource=='study': raise HTTP(400, json.dumps({"error":1,
            "description": "Only the creation of new studies is currently supported"}))
        
        # we're creating a new study (possibly with import instructions in the payload)
        cc0_agreement = kwargs.get('cc0_agreement', '')
        import_option = kwargs.get('import_option', '')
        treebase_id = kwargs.get('treebase_id', '')
        publication_doi = kwargs.get('publication_DOI', '')
        publication_ref = kwargs.get('publication_reference', '')
        ##dryad_DOI = kwargs.get('dryad_DOI', '')

        # check for required license agreement!
        if cc0_agreement != 'true': raise HTTP(400, json.dumps({"error":1,
            "description": "CC-0 license must be accepted to add studies using this API."}))

        auth_info = api_utils.authenticate(**kwargs)

        gd = GitData(repo=repo_path, remote=repo_remote, git_ssh=git_ssh, pkey=pkey)
        # studies created by the OpenTree API start with o,
        # so they don't conflict with new study id's from other sources
        new_resource_id = "o%d" % (gd.newest_study_id() + 1)

        # start with an empty NexSON template 
        app_name = "api"
        new_study_nexson = get_empty_nexson("1.2.1")
        nexml = new_study_nexson['nexml']
        nexml['^ot:studyId'] = new_resource_id
        # add known values for its metatags
        meta_publication_reference = None
        importing_from_crossref_API = (import_option == 'IMPORT_FROM_PUBLICATION_DOI' and publication_doi) or \
                                      (import_option == 'IMPORT_FROM_PUBLICATION_REFERENCE' and publication_ref)

        if importing_from_crossref_API:
            if import_option == 'IMPORT_FROM_PUBLICATION_DOI':
                # if curator has provided a DOI, use it to pre-populate study metadata
                # Cleanup submitted DOI to work with CrossRef API.
                #   WORKS: http://dx.doi.org/10.999...
                #   WORKS: doi:10.999...
                #   FAILS: doi: 10.999...
                #   FAILS: DOI:10.999...
                # Let's keep it simple and make it a bare DOI.
                # All DOIs use the directory indicator '10.', see
                #   http://www.doi.org/doi_handbook/2_Numbering.html#2.2.2
                # Remove all whitespace from the submitted DOI...
                publication_doi = "".join(publication_doi.split())
                # ... then strip everything up to the first '10.'
                doi_parts = publication_doi.split('10.')
                doi_parts[0] = ''
                search_term = '10.'.join(doi_parts)
            else:  # assumes IMPORT_FROM_PUBLICATION_REFERENCE
                search_term = publication_ref
            u = 'http://search.crossref.org/dois?' + urlencode({'q': search_term})
            doi_lookup_response = fetch(u)
            doi_lookup_response = unicode(doi_lookup_response, 'utf-8')   # make sure it's Unicode!
            try:
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
                    meta_publication_url = match.get('doi')  # already in URL form
                    if meta_publication_url:
                        nexml['^ot:studyPublication'] = {'@href': meta_publication_url}
                    meta_year = match.get('year')
                    if meta_year:
                        nexml['^ot:studyYear'] = meta_year
            except:
                if import_option == 'IMPORT_FROM_PUBLICATION_DOI':
                    meta_publication_reference = u'No matching publication found for this DOI!'
                else:  # assumes IMPORT_FROM_PUBLICATION_REFERENCE
                    meta_publication_reference = u'No matching publication found for this reference string'
        if meta_publication_reference:
            nexml['^ot:studyPublicationReference'] = meta_publication_reference
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
        master_file_blob_included = kwargs.get('included_SHA')
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
