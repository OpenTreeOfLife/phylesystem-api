from pyramid.view import view_config
# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
                                    HTTPException,
                                    HTTPError,
                                    HTTPNotFound, 
                                    HTTPBadRequest,
                                    HTTPInternalServerError,
                                    HTTPForbidden,
                                   )
from peyotl.api import OTI
import phylesystem_api.api_utils as api_utils
from phylesystem_api.api_utils import find_in_request
import json
from peyotl.phylesystem.git_workflows import GitWorkflowError, \
                                             validate_and_convert_nexson
from peyotl.nexson_syntax import get_empty_nexson, \
                                 extract_supporting_file_messages, \
                                 PhyloSchema, \
                                 read_as_json, \
                                 BY_ID_HONEY_BADGERFISH
from peyotl.external import import_nexson_from_treebase
import requests
import sys

def __extract_nexson_from_http_call(request, **kwargs):
    """Returns the nexson blob from `kwargs` or the request.body"""
    try:
        # check for kwarg 'nexson', or load the full request body
        if 'nexson' in kwargs:
            nexson = kwargs.get('nexson', {})
        else:
            nexson = request.json_body
        if not isinstance(nexson, dict):
            nexson = json.loads(nexson)
        if 'nexson' in nexson:
            nexson = nexson['nexson']
    except:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('Exception getting nexson content in __extract_nexson_from_http_call')
        raise HTTPBadRequest(json.dumps({"error": 1, "description": 'NexSON must be valid JSON'}))
    return nexson

def __extract_and_validate_nexson(request, repo_nexml2json, kwargs):
    try:
        nexson = __extract_nexson_from_http_call(request, **kwargs)
        #from peyotl.manip import count_num_trees
        #numtrees=count_num_trees(nexson,repo_nexml2json)
        #_LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        #_LOG.debug('number of trees in nexson is {}, max number of trees is {}'.format(numtrees,max_num_trees))
        repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
        bundle = validate_and_convert_nexson(nexson,
                                             repo_nexml2json,
                                             allow_invalid=False,
                                             max_num_trees_per_study=max_num_trees)
        nexson, annotation, validation_log, nexson_adaptor = bundle
    except GitWorkflowError as err:
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.exception('PUT failed in validation')
        raise HTTPBadRequest(err.msg or 'No message found')
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

def __validate_output_nexml2json(repo_nexml2json, kwargs, resource, type_ext, content_id=None):
    # sometimes we need to tweak the incoming kwargs, so let's 
    # make a mutable MultiDict copy of Pyramid's immutable NestedMultiDict
    kwargs = kwargs.copy()
    msg = None
    if 'output_nexml2json' not in kwargs:
        kwargs['output_nexml2json'] = '0.0.0'
    biv = kwargs.get('bracket_ingroup')
    if biv and isinstance(biv, str):
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
    except ValueError as x:
        #_LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        msg = str(x)
        #_LOG.exception('GET failing: {m}'.format(m=msg))
    if msg:
        #_LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        #_LOG.debug('output sniffing err msg = ' + msg)
        raise HTTPBadRequest(json.dumps({"error": 1, "description": msg}))
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
        # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
        # _LOG.debug('annotated_commit failed')
        raise HTTPBadRequest(body=json.dumps(annotated_commit))
    return annotated_commit

def check_not_read_only():
    if api_utils.READ_ONLY_MODE:
        raise HTTPForbidden(anyjson.dumps({"error": 1, "description": "phylesystem-api running in read-only mode"}))
    return True

def __deferred_push_to_gh_call(request, resource_id, doc_type='nexson', **kwargs):
    check_not_read_only()
    try:
        from open_tree_tasks import call_http_json
        #_LOG.debug('call_http_json imported')
    except:
        call_http_json = None
        _LOG = api_utils.get_logger(request, 'ot_api.default.v3')
        _LOG.debug('call_http_json was not imported from open_tree_tasks')
    if call_http_json is not None:
        # Pass the resource_id in data, so that two-part collection IDs will be recognized
        # (else the second part will trigger an unwanted JSONP response from the push)
        url = api_utils.compose_push_to_github_url(request, resource_id=None)
        auth_token = copy.copy(kwargs.get('auth_token'))
        data = {'doc_type': doc_type, 'resource_id': resource_id}
        if auth_token is not None:
            data['auth_token'] = auth_token
        call_http_json.delay(url=url, verb='PUT', data=data)

@view_config(route_name='fetch_study', renderer='json')
def fetch_study(request):
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
    
    api_version = request.matchdict['api_version']
    study_id = request.matchdict['study_id']
    content_id = None
    version_history = None
    comment_html = None
    final_path_part = request.path.split('/')[-1]
    # does this look like a filename? if so, grab its extension
    try: 
        request_extension = final_path_part.split('.')[1]
        if request_extension not in('html', 'json'): 
            request_extension = '.{}'.format(request_extension)
    except IndexError:
        request_extension = None
    try:
        json_data = request.json_body
    except:
        # no JSON payload provided
        json_data = {}
    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    out_schema = __validate_output_nexml2json(repo_nexml2json,
                                              json_data,
                                              'study',
                                              request_extension,
                                              content_id=content_id)
    parent_sha = find_in_request(request, 'starting_commit_SHA', None)
    # _LOG.debug('parent_sha = {}'.format(parent_sha))
    # return the correct nexson of study_id, using the specified view
    try:
        r = phylesystem.return_study(study_id, commit_sha=parent_sha, return_WIP_map=True)
    except:
        # _LOG.exception('GET failed')
        raise HTTPNotFound(body=json.dumps({"error": 1, "description": 'Study #%s GET failure' % study_id}))
    try:
        study_nexson, head_sha, wip_map = r
        blob_sha = phylesystem.get_blob_sha_for_study_id(study_id, head_sha)
        phylesystem.add_validation_annotation(study_nexson, blob_sha)
        version_history = phylesystem.get_version_history_for_study_id(study_id)
        try:
            comment_html = api_utils.markdown_to_html(study_nexson['nexml']['^ot:comment'], open_links_in_new_window=True )
        except:
            comment_html = ''
    except:
        # _LOG.exception('GET failed')
        e = sys.exc_info()[0]
        raise HTTPBadRequest(e)

    if out_schema.format_str == 'nexson' and out_schema.version == repo_nexml2json:
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
            raise HTTPBadRequest(msg)

    if out_schema.is_json():
        try:
            study_DOI = study_nexson['nexml']['^ot:studyPublication']['@href']
        except KeyError:
            study_DOI = None
        try:
            duplicate_study_ids = _fetch_duplicate_study_ids(study_DOI, study_id)
        except:
            # _LOG.exception('call to OTI check for duplicate DOIs failed')
            duplicate_study_ids = None

        try:
            shard_name = _fetch_shard_name(study_id)
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

@view_config(route_name='create_study', renderer='json', request_method='OPTIONS')
@view_config(route_name='study_CORS_preflight', renderer='json')
def study_CORS_preflight(request):
    api_utils.raise_on_CORS_preflight(request)

@view_config(route_name='create_study', renderer='json', request_method='POST')
def create_study(request):
    api_version = request.matchdict['api_version']

    # this method requires authentication
    auth_info = api_utils.authenticate(request)

    # gather any user-provided git-commit message
    try:
        commit_msg = find_in_request(request, 'commit_msg','')
        if commit_msg.strip() == '':
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    api_utils.raise_if_read_only()

    # we're creating a new study (possibly with import instructions in the payload)
    import_from_location = find_in_request(request, 'import_from_location', '')
    treebase_id = find_in_request(request, 'treebase_id', '')
    nexml_fetch_url = find_in_request(request, 'nexml_fetch_url', '')
    nexml_pasted_string = find_in_request(request, 'nexml_pasted_string', '')
    publication_doi = find_in_request(request, 'publication_DOI', '')
    # if a URL or something other than a valid DOI was entered, don't submit it to crossref API
    publication_doi_for_crossref = __make_valid_DOI(publication_doi) or None
    publication_ref = find_in_request(request, 'publication_reference', '')
    # is the submitter explicity applying the CC0 waiver to a new study?
    cc0_agreement = (find_in_request(request, 'chosen_license', '') == 'apply-new-CC0-waiver' and
                     find_in_request(request, 'cc0_agreement', '') == 'true')
    # look for the chosen import method, e.g,
    # 'import-method-PUBLICATION_DOI' or 'import-method-MANUAL_ENTRY'
    import_method = find_in_request(request, 'import_method', '')
    ##dryad_DOI = find_in_request(request, 'dryad_DOI', '')

    # Create initial study NexSON using the chosen import method.
    #
    # N.B. We're currently using a streamlined creation path with just
    # two methods (TreeBASE ID and publication DOI). But let's keep the
    # logic for others, just in case we revert based on user feedback.
    importing_from_treebase_id = (import_method == 'import-method-TREEBASE_ID' and treebase_id != '')
    importing_from_nexml_fetch = (import_method == 'import-method-NEXML' and nexml_fetch_url)
    importing_from_post_arg = (import_method == 'import-method-POST')
    importing_from_nexml_string = (import_method == 'import-method-NEXML' and nexml_pasted_string)
    importing_from_crossref_API = (import_method == 'import-method-PUBLICATION_DOI' and publication_doi_for_crossref) or \
                                  (import_method == 'import-method-PUBLICATION_REFERENCE' and publication_ref)

    # Are they using an existing license or waiver (CC0, CC-BY, something else?)
    using_existing_license = (find_in_request(request, 'chosen_license', '') == 'study-data-has-existing-license')

    # any of these methods should returna parsed NexSON dict (vs. string)
    if importing_from_treebase_id:
        # make sure the treebase ID is an integer
        treebase_id = "".join(treebase_id.split())  # remove all whitespace
        treebase_id = treebase_id.lstrip('S').lstrip('s')  # allow for possible leading 'S'?
        try:
            treebase_id = int(treebase_id)
        except ValueError as e:
            raise HTTPBadRequest(json.dumps({
                "error": 1,
                "description": "TreeBASE ID should be a simple integer, not '%s'! Details:\n%s" % (treebase_id, e.message)
            }))
        try:
            new_study_nexson = import_nexson_from_treebase(treebase_id, nexson_syntax_version=BY_ID_HONEY_BADGERFISH)
        except Exception as e:
            raise HTTPInternalServerError(json.dumps({
                "error": 1,
                "description": "Unexpected error parsing the file obtained from TreeBASE. Please report this bug to the Open Tree of Life developers."
            }))
    elif importing_from_crossref_API:
        new_study_nexson = _new_nexson_with_crossref_metadata(doi=publication_doi_for_crossref, ref_string=publication_ref, include_cc0=cc0_agreement)
    elif importing_from_post_arg:
        phylesystem = api_utils.get_phylesystem(request)
        repo_nexml2json = phylesystem.repo_nexml2json
        bundle = __extract_and_validate_nexson(request,
                                               repo_nexml2json,
                                               request.json_body)
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
            existing_license = find_in_request(request, 'alternate_license', '')
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
                alt_license_name = find_in_request(request, 'alt_license_name', '')
                alt_license_url = find_in_request(request, 'alt_license_URL', '')
                # OK to add a name here? mainly to capture submitter's intent
                nexml['^xhtml:license'] = {'@name': alt_license_name, '@href': alt_license_url}

    nexml['^ot:curatorName'] = auth_info.get('name', '')

    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    new_study_id = None  # TODO: should we ever specify an ID here?
    try:
        r = phylesystem.ingest_new_study(new_study_nexson,
                                         repo_nexml2json,
                                         auth_info,
                                         new_study_id)
        new_resource_id, commit_return = r
    except GitWorkflowError as err:
        raise HTTPBadRequest(err.msg)
    except:
        raise HTTPBadRequest(traceback.format_exc())
    if commit_return['error'] != 0:
        # _LOG.debug('ingest_new_study failed with error code')
        raise HTTPBadRequest(json.dumps(commit_return))
    __deferred_push_to_gh_call(request, new_resource_id, doc_type='nexson', **request.json_body)
    return commit_return


@view_config(route_name='update_study', renderer='json')
def update_study(request):
    api_version = request.matchdict['api_version']
    study_id = request.matchdict['study_id']

    # this method requires authentication
    auth_info = api_utils.authenticate(request)

    parent_sha = find_in_request(request, 'starting_commit_SHA')
    if parent_sha is None:
        raise HTTPBadRequest('Expecting a "starting_commit_SHA" argument with the SHA of the parent')
    master_file_blob_included = find_in_request(request, 'merged_SHA')

    # gather any user-provided git-commit message
    try:
        commit_msg = find_in_request(request, 'commit_msg','')
        if commit_msg.strip() == '':
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    api_utils.raise_if_read_only()

    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
    bundle = __extract_and_validate_nexson(request,
                                           repo_nexml2json,
                                           request.json_body)
    nexson, annotation, nexson_adaptor = bundle
    try:
        gd = phylesystem.create_git_action(study_id)
    except KeyError as err:
        # _LOG.debug('PUT failed in create_git_action (probably a bad study ID)')
        raise HTTPBadRequest("invalid study ID, please check the URL")
    try:
        blob = __finish_write_verb(phylesystem,
                                   gd,
                                   nexson=nexson,
                                   resource_id=study_id,
                                   auth_info=auth_info,
                                   adaptor=nexson_adaptor,
                                   annotation=annotation,
                                   parent_sha=parent_sha,
                                   commit_msg=commit_msg,
                                   master_file_blob_included=master_file_blob_included)
    except GitWorkflowError as err:
        # _LOG.exception('PUT failed in __finish_write_verb')
        raise HTTPBadRequest(err.msg)
    #TIMING = api_utils.log_time_diff(_LOG, 'blob creation', TIMING)
    mn = blob.get('merge_needed')
    if (mn is not None) and (not mn):
        __deferred_push_to_gh_call(request, study_id, doc_type='nexson', **request.json_body)
    # Add updated commit history to the blob
    blob['versionHistory'] = phylesystem.get_version_history_for_study_id(study_id)
    return blob


@view_config(route_name='delete_study', renderer='json')
def delete_study(request):
    api_version = request.matchdict['api_version']
    study_id = request.matchdict['study_id']

    # this method requires authentication
    auth_info = api_utils.authenticate(request)

    # gather any user-provided git-commit message
    try:
        commit_msg = find_in_request(request, 'commit_msg','')
        if commit_msg.strip() == '':
            # git rejects empty commit messages
            commit_msg = None
    except:
        commit_msg = None

    api_utils.raise_if_read_only()

    phylesystem = api_utils.get_phylesystem(request)
    try:
        x = phylesystem.delete_study(study_id, auth_info, parent_sha, commit_msg=commit_msg)
        if x.get('error') == 0:
            __deferred_push_to_gh_call(request, None, doc_type='nexson', **request.json_body)
        return x
    except GitWorkflowError as err:
        raise HTTPBadRequest(err.msg)
    except:
        # _LOG.exception('Exception getting nexson content in phylesystem.delete_study')
        raise HTTPBadRequest(json.dumps({"error": 1, "description": 'Unknown error in study deletion'}))

@view_config(route_name='get_study_file_list', renderer='json')
@view_config(route_name='get_study_single_file', renderer='json')
def get_study_file(request):
    api_utils.raise_on_CORS_preflight(request)

    api_version = request.matchdict['api_version']
    study_id = request.matchdict['study_id']
    file_id = request.matchdict.get('file_id', None)

    result_data = None
    try:
        json_data = request.json_body
    except:
        # no JSON payload provided
        json_data = {}
    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    out_schema = __validate_output_nexml2json(repo_nexml2json,
                                              json_data,
                                              'file',
                                              None,
                                              content_id=study_id)
    parent_sha = find_in_request(request, 'starting_commit_SHA', None)
    try:
        r = phylesystem.return_study(study_id, commit_sha=parent_sha, return_WIP_map=True)
    except:
        # _LOG.exception('GET failed')
        raise HTTPNotFound(body=json.dumps({"error": 1, "description": 'Study #%s GET failure' % study_id}))
    study_nexson, head_sha, wip_map = r
    # TODO: return a description of the requested file, or a list of all files
    m_list = extract_supporting_file_messages(study_nexson)
    if file_id is None:
        r = []
        for m in m_list:
            files = m.get('data', {}).get('files', {}).get('file', [])
            for f in files:
                if '@url' in f:
                    r.append({'id': m['@id'],
                              'filename': f.get('@filename', ''),
                              'url_fragment': f['@url']})
                    break
        return r
    else:
        try:
            matching = None
            for m in m_list:
                if m['@id'] == file_id:
                    matching = m
                    break
            if matching is None:
                raise HTTPNotFound(body='No file with id="{f}" found in study="{s}"'.format(f=file_id, s=study_id))
            u = None
            files = m.get('data', {}).get('files', {}).get('file', [])
            for f in files:
                if '@url' in f:
                    u = f['@url']
                    break
            if u is None:
                raise HTTPNotFound(body='No @url found in the message with id="{f}" found in study="{s}"'.format(f=file_id, s=study_id))
            #TEMPORARY HACK TODO
            u = u.replace('uploadid=', 'uploadId=')
            #TODO: should not hard-code this, I suppose... (but not doing so requires more config...)
            if u.startswith('/curator'):
                u = 'https://tree.opentreeoflife.org' + u
            request.response.headers['Content-Type'] = 'text/plain'
            fetched = requests.get(u)
            fetched.raise_for_status()
            return fetched.text
        except Exception as x:
            # _LOG.exception('file_get failed')
            raise HTTPNotFound(body='Could not retrieve file. Exception: "{}"'.format(str(x)))


@view_config(route_name='get_study_external_url', renderer='json')
def get_study_external_url(request):
    api_utils.raise_on_CORS_preflight(request)

    api_version = request.matchdict['api_version']
    study_id = request.matchdict['study_id']

    phylesystem = api_utils.get_phylesystem(request)
    try:
        u = phylesystem.get_public_url(study_id)
        return json.dumps({'url': u, 'study_id': study_id})
    except:
        raise HTTPNotFound(body='{"error": 1, "description": "study not found"}')

@view_config(route_name='get_study_tree', renderer='json')
def get_study_tree(request):
    api_utils.raise_on_CORS_preflight(request)

    api_version = request.matchdict['api_version']
    study_id = request.matchdict['study_id']
    tree_id_with_extension = request.matchdict['tree_id_with_extension']
    tree_name_parts = tree_id_with_extension.split('.')
    tree_id = tree_name_parts[0]
    if len(tree_name_parts) > 1:
        file_ext = ".{}".format(tree_name_parts[1])
    else:
        file_ext = None

    result_data = None
    try:
        json_data = request.json_body
    except:
        # no JSON payload provided
        json_data = {}
    phylesystem = api_utils.get_phylesystem(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    out_schema = __validate_output_nexml2json(repo_nexml2json,
                                              json_data,
                                              'tree',
                                              file_ext,
                                              content_id=tree_id)
    parent_sha = find_in_request(request, 'starting_commit_SHA', None)
    try:
        r = phylesystem.return_study(study_id, commit_sha=parent_sha, return_WIP_map=True)
    except:
        # _LOG.exception('GET failed')
        raise HTTPNotFound(body=json.dumps({"error": 1, "description": 'Study #%s GET failure' % study_id}))

    try:
        study_nexson, head_sha, wip_map = r
        blob_sha = phylesystem.get_blob_sha_for_study_id(study_id, head_sha)
        phylesystem.add_validation_annotation(study_nexson, blob_sha)
        version_history = phylesystem.get_version_history_for_study_id(study_id)
        try:
            comment_html = api_utils.markdown_to_html(study_nexson['nexml']['^ot:comment'], open_links_in_new_window=True )
        except:
            comment_html = ''
    except:
        # _LOG.exception('GET failed')
        e = sys.exc_info()[0]
        raise HTTPBadRequest(e)

    try:
        serialize = not out_schema.is_json()
        src_schema = PhyloSchema('nexson', version=repo_nexml2json)
        result_data = out_schema.convert(study_nexson,
                                         serialize=serialize,
                                         src_schema=src_schema)
    except:
        msg = "Exception in coercing to the required NexSON version for validation. "
        # _LOG.exception(msg)
        raise HTTPBadRequest( msg)

    if result_data is None:
        raise HTTPNotFound(body='subresource "tree/{t}" not found in study "{s}"'.format(t=tree_id,
                                                                                 s=study_id))
    return result_data
