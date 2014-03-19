import os, sys
import time
import json
import anyjson
import hashlib
import github
from sh import git
from peyotl import can_convert_nexson_forms, convert_nexson_format
from github import Github, BadCredentialsException
import api_utils
from pprint import pprint
from gitdata import GitData
from locket import LockError
from gluon.tools import fetch
from urllib import urlencode
from gluon.html import web2pyHTMLParser
from peyotl.nexson_syntax import get_ot_study_info_from_nexml, BADGER_FISH_NEXSON_VERSION
from StringIO import StringIO

# NexSON validation
from peyotl.nexson_validation import NexsonWarningCodes, validate_nexson

_VALIDATING = False
_LOG = api_utils.get_logger('ot_api.default')
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

def _acquire_lock_or_exit(git_data, fail_msg=''):
    '''Adapts LockError to HTTP. If an exception is not thrown, the gd has the lock (and must release it!)
    '''
    try:
        git_data.acquire_lock()
    except LockError, e:
        msg = '{o} Details: {d}'.format(o=fail_msg, d=e.message)
        _LOG.debug(msg)
        raise HTTP(400, json.dumps({
            "error": 1,
            "description": msg 
        }))
@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = 86400  # cache for a day

    repo_path, repo_remote, git_ssh, pkey, repo_nexml2json = api_utils.read_config(request)
    git_env     = {"GIT_SSH": git_ssh, "PKEY": pkey}

    def __validate(nexson):
        '''Returns three objects:
            an annotation dict (NexSON formmatted), 
            the validation_log object created when NexSON validation was performed, and
            the object of class NexSON which was created from nexson. This object will
                alias parts of the nexson dict that is passed in as an argument.
        '''
        # stub function for hooking into NexSON validation
        codes_to_skip = [NexsonWarningCodes.UNVALIDATED_ANNOTATION]
        v_log, adaptor = validate_nexson(nexson, codes_to_skip, retain_deprecated=True)
        script_name = 'api.opentreeoflife.org/validate' # TODO
        annotation = v_log.prepare_annotation(author_name=script_name,
                                              description="Open Tree NexSON validation")
        return annotation, v_log, adaptor

    def __finish_write_verb(git_data, 
                            git_hub_auth,
                            nexson,
                            author_name,
                            author_email,
                            resource_id,
                            adaptor,
                            annotation):
        '''Called by PUT and POST handlers to avoid code repetition.'''
        # global TIMING
        #TODO, need to make this spawn a thread to do the second commit rather than block
        block_until_annotation_commit = False
        unadulterated_content_commit = do_commit(git_data, git_hub_auth, nexson, author_name, author_email, resource_id)
        # TIMING = api_utils.log_time_diff(_LOG, 'unadulterated commit', TIMING)
        if unadulterated_content_commit['error'] != 0:
            _LOG.debug('unadulterated_content_commit failed')
            raise HTTP(400, json.dumps(unadulterated_content_commit))
        if _VALIDATING and block_until_annotation_commit:
            # add the annotation and commit the resulting blob...
            adaptor.add_or_replace_annotation(annotation)
            nexson = adaptor.get_nexson_str()
            annotated_commit = do_commit(git_data, git_hub_auth, nexson, author_name, author_email, resource_id)
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
        output_nexml2json = kwargs.get('output_nexml2json', '0.0.0')
        if (output_nexml2json != repo_nexml2json) and not can_convert_nexson_forms(repo_nexml2json, output_nexml2json):
            msg = 'Cannot convert from {s} to {d}'.format(s=repo_nexml2json, d=output_nexml2json)
            _LOG.debug('GET failing: {m}'.format(m=msg))
            raise HTTP(400, json.dumps({"error": 1, "description": msg}))
        if resource not in valid_resources:
            raise HTTP(400, json.dumps({"error": 1,
                "description": 'Resource requested not in list of valid resources: %s' % valid_resources }))

        # support JSONP request from another domain
        if jsoncallback or callback:
            response.view = 'generic.jsonp'

        # fetch using the GitHub API auth-token for a logged-in curator
        auth_token = kwargs.get('auth_token', 'ANONYMOUS')
        if auth_token == 'ANONYMOUS':
            # non-web callers might be using an HTTP header ("Authorization: token abc123def456")
            auth_header = request.env.get('http_authorization', None) or request.wsgi.environ.get('HTTP_AUTHORIZATION', None)
            if auth_header:
                auth_token = auth_header.split()[1]

        # return the correct nexson of study_id, using the specified view
        gd = GitData(repo=repo_path)
        _acquire_lock_or_exit(gd)
        try:
            gd.checkout_master()
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
        nexml_fetch_url = kwargs.get('nexml_fetch_url', '')
        nexml_pasted_string = kwargs.get('nexml_pasted_string', '')
        publication_doi = kwargs.get('publication_DOI', '')
        publication_ref = kwargs.get('publication_reference', '')
        ##dryad_DOI = kwargs.get('dryad_DOI', '')

        # check for required license agreement!
        if cc0_agreement != 'true': raise HTTP(400, json.dumps({"error":1,
            "description": "CC-0 license must be accepted to add studies using this API."}))

        (gh, author_name, author_email) = api_utils.authenticate(**kwargs)

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
            new_study_nexson = _import_nexson_from_treebase(treebase_id)
        elif importing_from_nexml_fetch:
            new_study_nexson = _import_nexson_from_nexml(fetch_url=nexml_fetch_url)
        elif importing_from_nexml_string:
            new_study_nexson = _import_nexson_from_nexml(nexml=nexml_pasted_string)
        elif importing_from_crossref_API:
            new_study_nexson = _new_nexson_with_crossref_metadata(doi=publication_doi, ref_string=publication_ref)
        else:   # assumes IMPORT_FROM_MANUAL_ENTRY, or insufficient args above
            new_study_nexson = _new_nexson()

        # TODO: ensure that we have standard structures? esp. study metadata fields!

        # apply standard metatags for a new study, regardless of NexSON source
        if new_study_nexson.has_key('nex:nexml'):  # from TreeBASE
            study_metatags = new_study_nexson['nex:nexml']['meta']
        else:  # from our template
            study_metatags = new_study_nexson['nexml']['meta']
            
        for tag in study_metatags:
            if not '@property' in tag:
                continue
            if tag['@property'] == u'ot:studyId':
                tag['$'] = u'REPLACE_WITH_NEW_ID'
            if tag['@property'] == u'ot:curatorName':
                tag['$'] = kwargs.get('author_name', '').decode('utf-8')

        # add nexson to kwargs for full validation
        kwargs['nexson'] = new_study_nexson
        nexson, annotation, validation_log, nexson_adaptor = __validate_and_normalize_nexson(**kwargs)
        # Now we have a validated nexson string, unpacked from __validate_etc
        # TODO: Should we add the annotation generated above?!

        gd = GitData(repo=repo_path)
        # studies created by the OpenTree API start with o,
        # so they don't conflict with new study id's from other sources
        new_resource_id = "o%d" % (gd.newest_study_id() + 1)

        # do a quick substitution using the new ID
        nexson = nexson.replace('REPLACE_WITH_NEW_ID', new_resource_id)

        return __finish_write_verb(gd,
                                   gh,
                                   nexson,
                                   author_name,
                                   author_email,
                                   new_resource_id,
                                   nexson_adaptor,
                                   annotation)

    def __coerce_nexson_format(nexson, dest_format, current_format=None):
        '''Calls convert_nexson_format but does the appropriate logging and HTTP exceptions.
        '''
        try:
            return convert_nexson_format(nexson, dest_format, current_format=current_format)
        except:
            msg = "Exception in coercing to the required NexSON version for validation"
            _LOG.exception(msg)
            raise HTTP(400, json.dumps({"error": 1, "description": msg}))

    def __validate_and_normalize_nexson(**kwargs):
        """A wrapper around __validate() which also sorts JSON keys and checks for invalid JSON"""
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
            _LOG.exception('Exception getting nexson content in __validate_and_normalize_nexson')
            raise HTTP(400, json.dumps({"error": 1, "description": 'NexSON must be valid JSON'}))
        #TEMP
        VALIDATION_NEXSON_FORMAT = "0.0.0" #currently the nexson validator requires badgerfish
        nexson = __coerce_nexson_format(nexson, VALIDATION_NEXSON_FORMAT)
        
        annotation, validation_log, nexson_adaptor = __validate(nexson)
        if _VALIDATING and validation_log.errors:
            _LOG.debug('__validate failed'.format(k=nexson.keys(), a=json.dumps(annotation)))
            raise HTTP(400, json.dumps(annotation))
        nexson = __coerce_nexson_format(nexson, repo_nexml2json)
        # sort the keys of the POSTed NexSON and indent 0 spaces
        nexson = json.dumps(nexson, sort_keys=True, indent=0)

        return nexson, annotation, validation_log, nexson_adaptor

    def PUT(resource, resource_id, **kwargs):
        "Open Tree API methods relating to updating existing resources"
        # global TIMING
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study':
            _LOG.debug('resource must be "study"')
            raise HTTP(400, 'resource != study')
        # TIMING = api_utils.log_time_diff(_LOG)
        gh, author_name, author_email = api_utils.authenticate(**kwargs)
        # TIMING = api_utils.log_time_diff(_LOG, 'github authentication', TIMING)
        
        nexson, annotation, validation_log, nexson_adaptor = __validate_and_normalize_nexson(**kwargs)
        # TIMING = api_utils.log_time_diff(_LOG, 'validation and normalization', TIMING)
        gd = GitData(repo=repo_path)

        # We compare sha1's instead of the actual data to reduce memory use
        # when comparing large studies
        posted_nexson_sha1 = hashlib.sha1(nexson).hexdigest()
        nexson_fetched_content, head_sha = gd.return_study(resource_id)
        nexson_sha1 = hashlib.sha1(nexson_fetched_content).hexdigest()
        # TIMING = api_utils.log_time_diff(_LOG, 'GitData creation and sha', TIMING)

        # the POSTed data is the same as what we currently have, do nothing and return successfully
        if posted_nexson_sha1 == nexson_sha1:
            return { "error": 0, "description": "success, nothing to update" };
        blob = __finish_write_verb(gd,
                                   gh,
                                   nexson,
                                   author_name,
                                   author_email,
                                   resource_id,
                                   nexson_adaptor,
                                   annotation)
        # TIMING = api_utils.log_time_diff(_LOG, 'blob creation', TIMING)
        return blob

 
    def _pull_gh(gd, repo_remote, branch_name, resource_id):#
        try:
            # TIMING = api_utils.log_time_diff(_LOG, 'lock acquisition', TIMING)
            git(gd.gitdir, "fetch", repo_remote, _env=git_env)
            git(gd.gitdir, gd.gitwd, "merge", repo_remote + '/' + branch_name, _env=git_env)
            # TIMING = api_utils.log_time_diff(_LOG, 'git pull', TIMING)
        except Exception, e:
            # We can ignore this if the branch doesn't exist yet on the remote,
            # otherwise raise a 400
#            raise #@EJM what was this doing?
            if "not something we can merge" not in e.message:
                # Attempt to abort a merge, in case of conflicts
                try:
                    git(gd.gitdir,"merge", "--abort")
                except:
                    pass
                msg = "Could not pull or merge latest %s branch from %s ! Details: \n%s" % (branch_name, repo_remote, e.message)
                _LOG.debug(msg)
                raise HTTP(400, json.dumps({
                    "error": 1,
                    "description": msg
                }))

    
    def _push_gh(gd,repo_remote,branch_name,resource_id):#
        try:
            # actually push the changes to Github
            gd.push(repo_remote, env=git_env, branch=branch_name)
        except Exception, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not push deletion of study #%s! Details:\n%s" % (resource_id, e.message)
            }))

    def _new_nexson():
        # return an empty NexSON doc using a template file
        app_name = "api"
        template_filename = "%s/applications/%s/static/NEXSON_TEMPLATE.json" % (request.env.web2py_path, app_name)
        nexson = json.load( open(template_filename) )
        return nexson

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
        nexson = _new_nexson()
        study_metatags = nexson['nexml']['meta']
        for tag in study_metatags:
            if not '@property' in tag:
                continue
            if tag['@property'] == u'ot:studyPublicationReference':
                tag['$'] = meta_publication_reference
            if tag['@property'] == u'ot:studyPublication':
                # N.B. here we set @href instead
                tag['@href'] = meta_publication_url
            if tag['@property'] == u'ot:studyYear':
                tag['$'] = meta_year

        return nexson

    def _import_nexson_from_nexml(nexml=None, fetch_url=None):
        # Use Open Tree API tools to convert NeXML to NexSON, then groom it to
        # fit our standards.
        if fetch_url:
            nexml = fetch(fetch_url)
            nexml = unicode(nexml, 'utf-8')   # make sure it's Unicode!

        # convert from NeXML to basic (BadgerFish) NexSON
        fakefile = StringIO(nexml)  # the method we're calling expects a file  :-/
        nexson = get_ot_study_info_from_nexml(fakefile,
                                              nexson_syntax_version=BADGER_FISH_NEXSON_VERSION)
        # TODO? get_ot_study_info_from_treebase_nexml() instead, if TreeBASE is source?
        return nexson

    def _import_nexson_from_treebase(treebase_id):
        # Use TreeBASE API to fetch NeXML, then pass it as a string
        # to _import_nexson_from_nexml()

        # EXAMPLE: Here's Phylografter's fetch URL for study 15515 as 'nexml' (versus 'nexus'):
        #   http://purl.org/phylo/treebase/phylows/study/TB2:S15515?format=nexml
        # ... which redirects to:
        #   http://treebase.org/treebase-web/phylows/study/TB2:S15515?format=nexml
        # ... which redirects to:
        #   http://treebase.org/treebase-web/search/downloadAStudy.html?id=15515&format=nexml
        #
        # Since gluon's fetch follows redirects, let's respect the PhyloWS API on treebase.org
        treebase_lookup_response = fetch(
            'http://treebase.org/treebase-web/phylows/study/TB2:S%d?format=nexml' % 
            treebase_id
        )
        treebase_lookup_response = unicode(treebase_lookup_response, 'utf-8')   # make sure it's Unicode!

        # convert this NeXML response to nexson
        return _import_nexson_from_nexml(nexml=treebase_lookup_response)

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

        if not resource=='study': raise HTTP(400, 'resource != study')

        (gh, author_name, author_email) = api_utils.authenticate(**kwargs)

        author       = "%s <%s>" % (author_name, author_email)

        branch_name  = "%s_study_%s" % (gh.get_user().login, resource_id)

        gd = GitData(repo=repo_path)

        _acquire_lock_or_exit(gd, fail_msg="Could not acquire lock to delete the study #%s" % resource_id)

        _pull_gh(gd,repo_remote,branch_name,resource_id)
        
        try:
            pass
            new_sha = gd.remove_study(resource_id, branch_name, author)
        except Exception, e:
        
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not remove study #%s! Details: %s" % (resource_id, e.message)
            }))

        _push_gh(gd,repo_remote,branch_name,resource_id)

        gd.release_lock()
        return {
            "error": 0,
            "branch_name": branch_name,
            "description": "Deleted study #%s" % resource_id,
            "sha":  new_sha
        }

            
    def OPTIONS(*args, **kwargs):
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200, **(response.headers))

    return locals()
