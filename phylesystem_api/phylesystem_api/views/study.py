from pyramid.view import view_config
# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.httpexceptions import (
                                    HTTPException,
                                    HTTPError,
                                    HTTPNotFound, 
                                    HTTPBadRequest,
                                    HTTPInternalServerError,
                                   )
from peyotl.api import OTI
import phylesystem_api.api_utils as api_utils
import json
from peyotl.nexson_syntax import get_empty_nexson, \
                                 extract_supporting_file_messages, \
                                 PhyloSchema, \
                                 read_as_json, \
                                 BY_ID_HONEY_BADGERFISH
from peyotl.external import import_nexson_from_treebase

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

@view_config(route_name='fetch_study', renderer='json')
def fetch_study(request):
    phylesystem = api_utils.get_phylesystem(request)
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
    repo_nexml2json = phylesystem.repo_nexml2json
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
        except ValueError as x:
            #_LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            msg = str(x)
            #_LOG.exception('GET failing: {m}'.format(m=msg))
        if msg:
            #_LOG = api_utils.get_logger(request, 'ot_api.default.v1')
            #_LOG.debug('output sniffing err msg = ' + msg)
            raise HTTPBadRequest(json.dumps({"error": 1, "description": msg}))
        return schema
    
    api_version = request.matchdict['api_version']
    study_id = request.matchdict['study_id']
    returning_full_study = False
    #content_id = None
    version_history = None
    comment_html = None
    final_path_part = request.path.split('/')[-1]
    # does this look like a filename? if so, grab its extension
    try: 
        request_extension = final_path_part.split('.')[1]
    except IndexError:
        request_extension = None
    if request_extension not in('html', 'json'):
        type_ext = '.{}'.format(request_extension)
    else:
        type_ext = None
    out_schema = __validate_output_nexml2json(request.params,
                                              'study',
                                              type_ext,
                                              content_id=content_id)



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
            raise HTTP(400, msg)
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

@view_config(route_name='create_study', renderer='json', request_method='OPTIONS')
@view_config(route_name='study_CORS_preflight', renderer='json')
def study_CORS_preflight(request):
    api_utils.raise_on_CORS_preflight(request)

@view_config(route_name='create_study', renderer='json', request_method='POST')
def create_study(request):
    phylesystem = api_utils.get_phylesystem(request)
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    pass

@view_config(route_name='update_study', renderer='json')
def update_study(request):
    phylesystem = api_utils.get_phylesystem(request)
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    pass

@view_config(route_name='delete_study', renderer='json')
def delete_study(request):
    phylesystem = api_utils.get_phylesystem(request)
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only_mode = api_utils.read_phylesystem_config(request)
    repo_nexml2json = phylesystem.repo_nexml2json
    pass

@view_config(route_name='get_study_file', renderer='json')
def get_study_file(request):
    api_utils.raise_on_CORS_preflight(request)
    pass

@view_config(route_name='get_study_external_url', renderer='json')
def get_study_external_url(request):
    api_utils.raise_on_CORS_preflight(request)
    pass

@view_config(route_name='get_study_tree', renderer='json')
def get_study_tree(request):
    api_utils.raise_on_CORS_preflight(request)
    pass

@view_config(route_name='get_study_tree_newick', renderer='json')
def get_study_tree_newick(request):
    api_utils.raise_on_CORS_preflight(request)
    pass




