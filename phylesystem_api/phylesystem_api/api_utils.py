from github import Github, BadCredentialsException
from peyotl.nexson_syntax import write_as_json
from peyotl.phylesystem import Phylesystem
from peyotl.collections_store import TreeCollectionStore
from peyotl.amendments import TaxonomicAmendmentStore
from peyotl.utility import read_config as read_peyotl_config
from configparser import ConfigParser
from datetime import datetime
# see exception subclasses at https://docs.pylonsproject.org/projects/pyramid/en/latest/api/httpexceptions.html
from pyramid.request import Request
from pyramid.httpexceptions import (
                                    HTTPException,
                                    HTTPOk,
                                    HTTPError,
                                    HTTPServerError,
                                    HTTPNotFound,
                                    HTTPBadRequest,
                                    HTTPInternalServerError,
                                    HTTPForbidden,
                                   )
from beaker.cache import cache_managers
import tempfile
import logging
import json
import requests
import os
import re
import copy
import threading
try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import xml.etree.ElementTree as ElementTree



_LOG = logging.getLogger('phylesystem_api')
_LOG.debug("start api_utils")



# this will be updated by config below; start safe by default
READ_ONLY_MODE = True

def get_private_dir(request):
    #app_name = request.application
    #leader = request.env.web2py_path
    #return '%s/applications/%s/private' % (leader, app_name)
    return "./private/"

def atomic_write_json_if_not_found(obj, dest, request):
    if os.path.exists(dest):
        return False
    dir = get_private_dir(request)
    handle, tmpfn = tempfile.mkstemp(suffix='.json', dir=dir, text=True)
    # mkstemp opens the file and returns a file descriptor,
    #   but we are using write_as_json to open with the right encoding
    os.close(handle)
    write_as_json(obj, tmpfn, indent=2, sort_keys=True)
    if os.path.exists(dest):
        return False
    os.rename(tmpfn, dest)
    return True

def compose_push_to_github_url(request, resource_id, doc_type):
    if resource_id is None:
        call = '{p}://{d}/v3/push_docstore_changes'.format(p=request.environ['wsgi.url_scheme'],
                                                           d=request.environ['HTTP_HOST'])
    else:
        call = '{p}://{d}/v3/push_docstore_changes/{dt}/{r}'.format(p=request.environ['wsgi.url_scheme'],
                                                                    d=request.environ['HTTP_HOST'],
                                                                    dt=doc_type,
                                                                    r=resource_id)
    _LOG.debug(call)
    return call


# this allows us to raise HTTP(...)
_PHYLESYSTEM = None
def get_phylesystem(request):
    global READ_ONLY_MODE
    global _PHYLESYSTEM
    _LOG.debug('@@@ checking for _PHYLESYSTEM singleton...READ_ONLY_MODE? {}'.format(READ_ONLY_MODE))
    if _PHYLESYSTEM is not None:
        _LOG.debug('@@@ FOUND it, returning now')
        return _PHYLESYSTEM
    _LOG.debug('@@@ NOT FOUND, creating now')
    from phylesystem_api.gitdata import GitData
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, READ_ONLY_MODE = read_phylesystem_config(request)
    peyotl_config, cfg_filename = read_peyotl_config()
    if 'phylesystem' not in peyotl_config.sections():
        peyotl_config.add_section('phylesystem')
    peyotl_config.set('phylesystem', 'max_file_size', max_filesize) #overrides peyotl config with max phylesytem-api filesize
    push_mirror = os.path.join(repo_parent, 'mirror')
    pmi = {
        'parent_dir': push_mirror,
        'remote_map': {
            'GitHubRemote': git_hub_remote,
            },
        }
    mirror_info = {'push':pmi}
    conf = get_conf_object(request)
    a = {}
    try:
        new_study_prefix = conf.get('apis', 'new_study_prefix')
        a['new_study_prefix'] = new_study_prefix
    except:
        pass
    _PHYLESYSTEM = Phylesystem(repos_par=repo_parent,
                               git_ssh=git_ssh,
                               pkey=pkey,
                               git_action_class=GitData,
                               mirror_info=mirror_info,
                               **a)
    _LOG.debug('[[[[[[ repo_nexml2json = {}'.format(_PHYLESYSTEM.repo_nexml2json))
    if READ_ONLY_MODE:
        _LOG.warn('phylesytem-api running in READ_ONLY_MODE')
    else:
        _LOG.warn('phylesytem-api NOT running in READ_ONLY_MODE')
    return _PHYLESYSTEM

_TREE_COLLECTION_STORE = None
def get_tree_collection_store(request):
    global _TREE_COLLECTION_STORE
    if _TREE_COLLECTION_STORE is not None:
        return _TREE_COLLECTION_STORE
#    _LOG = get_logger(request, 'ot_api')
    from phylesystem_api.gitdata import GitData
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize = read_collections_config(request)
    push_mirror = os.path.join(repo_parent, 'mirror')
    pmi = {
        'parent_dir': push_mirror,
        'remote_map': {
            'GitHubRemote': git_hub_remote,
            },
        }
    mirror_info = {'push':pmi}
    conf = get_conf_object(request)
    import pprint
    a = {}
    try:
        # any keyword args to pass along from config?
        #new_study_prefix = conf.get('apis', 'new_study_prefix')
        #a['new_study_prefix'] = new_study_prefix
        pass
    except:
        pass
    _TREE_COLLECTION_STORE = TreeCollectionStore(repos_par=repo_parent,
                                                 git_ssh=git_ssh,
                                                 pkey=pkey,
                                                 git_action_class=GitData, #TODO?
                                                 mirror_info=mirror_info,
                                                 **a)
    _LOG.debug('assumed_doc_version = {}'.format(_TREE_COLLECTION_STORE.assumed_doc_version))
    return _TREE_COLLECTION_STORE

_TAXONOMIC_AMENDMENT_STORE = None
def get_taxonomic_amendment_store(request):
    global _TAXONOMIC_AMENDMENT_STORE
    if _TAXONOMIC_AMENDMENT_STORE is not None:
        return _TAXONOMIC_AMENDMENT_STORE
#    _LOG = get_logger(request, 'ot_api')
    from phylesystem_api.gitdata import GitData
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize = read_amendments_config(request)
    push_mirror = os.path.join(repo_parent, 'mirror')
    pmi = {
        'parent_dir': push_mirror,
        'remote_map': {
            'GitHubRemote': git_hub_remote,
            },
        }
    mirror_info = {'push':pmi}
    conf = get_conf_object(request)
    import pprint
    a = {}
    try:
        # any keyword args to pass along from config?
        #new_study_prefix = conf.get('apis', 'new_study_prefix')
        #a['new_study_prefix'] = new_study_prefix
        pass
    except:
        pass
    _TAXONOMIC_AMENDMENT_STORE = TaxonomicAmendmentStore(repos_par=repo_parent,
                                                         git_ssh=git_ssh,
                                                         pkey=pkey,
                                                         git_action_class=GitData, #TODO?
                                                         mirror_info=mirror_info,
                                                         **a)
    _LOG.debug('assumed_doc_version = {}'.format(_TAXONOMIC_AMENDMENT_STORE.assumed_doc_version))
    return _TAXONOMIC_AMENDMENT_STORE


def get_failed_push_filepath(request, doc_type=None):
    filenames_by_content_type = {'nexson': "PUSH_FAILURE_nexson.json",
                                 'collection': "PUSH_FAILURE_collection.json",
                                 'amendment': "PUSH_FAILURE_amendment.json",
                                 'favorites': "PUSH_FAILURE_favorites.json"}
    content_type = doc_type or request.matchdict.get('doc_type', 'nexson')
    failure_filename = filenames_by_content_type[content_type]
    return os.path.join(get_private_dir(request), failure_filename)

def get_conf_object(request):
    # There's apparently no easy way to retrieve the fully parsed
    # configuration from within the app. But we can access the variables
    # from the [app:main] setion, so we'll retrieve the full path to
    # our chosen INI file from there.
    conf = ConfigParser(allow_no_value=True)
    localconfig_filename = request.registry.settings['config_file_path']
    if os.path.isfile(localconfig_filename):
        conf.readfp(open(localconfig_filename))
    return conf

def read_phylesystem_config(request):
    """Load settings for managing the main Nexson docstore"""
    conf = get_conf_object(request)
    repo_parent   = conf.get("apis","repo_parent")
    repo_remote = conf.get("apis", "repo_remote")
    try:
        git_ssh     = conf.get("apis", "git_ssh")
    except:
        git_ssh = 'ssh'
    try:
        pkey        = conf.get("apis", "pkey")
    except:
        pkey = None
    try:
        git_hub_remote = conf.get("apis", "git_hub_remote")
    except:
        git_hub_remote = 'git@github.com:OpenTreeOfLife'
    try:
        max_filesize = conf.get("filesize", "peyotl_max_file_size")
    except:
        max_filesize = '20000000'
    try:
        max_num_trees = conf.get("filesize", "validation_max_num_trees")
    except:
        max_num_trees = 65
    try:
        max_num_trees = int(max_num_trees)
    except ValueError:
            raise HTTPBadRequest( json.dumps({"error": 1, "description": 'max number of trees per study in config is not an integer'}))
    try:
        read_only = conf.get("apis", "read_only") == 'true'
    except:
        read_only = False
    return repo_parent, repo_remote, git_ssh, pkey, git_hub_remote, max_filesize, max_num_trees, read_only

def read_collections_config(request):
    """Load settings for a minor repo with shared tree collections"""
    conf = get_conf_object(request)
    collections_repo_parent   = conf.get("apis","collections_repo_parent")
    collections_repo_remote = conf.get("apis", "collections_repo_remote")
    try:
        git_ssh     = conf.get("apis", "git_ssh")
    except:
        git_ssh = 'ssh'
    try:
        pkey        = conf.get("apis", "pkey")
    except:
        pkey = None
    try:
        git_hub_remote = conf.get("apis", "git_hub_remote")
    except:
        git_hub_remote = 'git@github.com:OpenTreeOfLife'
    try:
        max_filesize = conf.get("filesize", "collections_max_file_size")
    except:
        max_filesize = '20000000'
    return collections_repo_parent, collections_repo_remote, git_ssh, pkey, git_hub_remote, max_filesize

def read_amendments_config(request):
    """Load settings for a minor repo with shared taxonomic amendments"""
    conf = get_conf_object(request)
    amendments_repo_parent   = conf.get("apis","amendments_repo_parent")
    amendments_repo_remote = conf.get("apis", "amendments_repo_remote")
    try:
        git_ssh     = conf.get("apis", "git_ssh")
    except:
        git_ssh = 'ssh'
    try:
        pkey        = conf.get("apis", "pkey")
    except:
        pkey = None
    try:
        git_hub_remote = conf.get("apis", "git_hub_remote")
    except:
        git_hub_remote = 'git@github.com:OpenTreeOfLife'
    try:
        max_filesize = conf.get("filesize", "amendments_max_file_size")
    except:
        max_filesize = '20000000'
    return amendments_repo_parent, amendments_repo_remote, git_ssh, pkey, git_hub_remote, max_filesize

def read_favorites_config(request):
    """Load settings for a minor repo with per-user 'favorites' information"""
    conf = get_conf_object(request)
    favorites_repo_parent   = conf.get("apis","favorites_repo_parent")
    favorites_repo_remote = conf.get("apis", "favorites_repo_remote")
    try:
        git_ssh     = conf.get("apis", "git_ssh")
    except:
        git_ssh = 'ssh'
    try:
        pkey        = conf.get("apis", "pkey")
    except:
        pkey = None
    try:
        git_hub_remote = conf.get("apis", "git_hub_remote")
    except:
        git_hub_remote = 'git@github.com:OpenTreeOfLife'
    return favorites_repo_parent, favorites_repo_remote, git_ssh, pkey, git_hub_remote

def read_logging_config(request):
    conf = get_conf_object(request)
    try:
        level = conf.get("logging", "level")
        if not level.strip():
            level = 'WARNING'
    except:
        level = 'WARNING'
    try:
        logging_format_name = conf.get("logging", "formatter")
        if not logging_format_name.strip():
            logging_format_name = 'NONE'
    except:
        logging_format_name = 'NONE'
    try:
        logging_filepath = conf.get("logging", "filepath")
        if not logging_filepath.strip():
            logging_filepath = None
    except:
        logging_filepath = None
    return level, logging_format_name, logging_filepath

def authenticate(request):
    """Verify that we received a valid Github authentication token

    This method takes a dict of keyword arguments and optionally
    over-rides the author_name and author_email associated with the
    given token, if they are present.

    Returns a PyGithub object, author name and author email.

    This method will return HTTP 400 if the auth token is not present
    or if it is not valid, i.e. if PyGithub throws a BadCredentialsException.

    """
    # this is the GitHub API auth-token for a logged-in curator
    auth_token   = find_in_request(request, 'auth_token', '')

    if not auth_token:
        raise HTTPBadRequest(json.dumps({
            "error": 1,
            "description":"You must provide an auth_token to authenticate to the OpenTree API"
        }))
    gh           = Github(auth_token)
    gh_user      = gh.get_user()
    auth_info = {}
    try:
        auth_info['login'] = gh_user.login
    except BadCredentialsException:
        raise HTTPBadRequest(json.dumps({
            "error": 1,
            "description":"You have provided an invalid or expired authentication token"
        }))
    # use the Github Oauth token to get a name/email if not specified
    # we don't provide these as default values above because they would
    # generate API calls regardless of author_name/author_email being specifed
    auth_info['name'] = find_in_request(request, 'author_name', gh_user.name)
    auth_info['email'] = find_in_request(request, 'author_email', gh_user.email)
    return auth_info

''' ## using logging module directly
_LOGGING_LEVEL_ENVAR="OT_API_LOGGING_LEVEL"
_LOGGING_FORMAT_ENVAR="OT_API_LOGGING_FORMAT"
_LOGGING_FILE_PATH_ENVAR = 'OT_API_LOG_FILE_PATH'

def _get_logging_level(s=None):
    if s is None:
        return logging.NOTSET
    supper = s.upper()
    if supper == "NOTSET":
        level = logging.NOTSET
    elif supper == "DEBUG":
        level = logging.DEBUG
    elif supper == "INFO":
        level = logging.INFO
    elif supper == "WARNING":
        level = logging.WARNING
    elif supper == "ERROR":
        level = logging.ERROR
    elif supper == "CRITICAL":
        level = logging.CRITICAL
    else:
        level = logging.NOTSET
    return level

def _get_logging_formatter(s=None):
    if s is None:
        s == 'NONE'
    else:
        s = s.upper()
    rich_formatter = logging.Formatter("[%(asctime)s] %(filename)s (%(lineno)d): %(levelname) 8s: %(message)s")
    simple_formatter = logging.Formatter("%(levelname) 8s: %(message)s")
    raw_formatter = logging.Formatter("%(message)s")
    default_formatter = None
    logging_formatter = default_formatter
    if s == "RICH":
        logging_formatter = rich_formatter
    elif s == "SIMPLE":
        logging_formatter = simple_formatter
    else:
        logging_formatter = None
    if logging_formatter is not None:
        logging_formatter.datefmt='%H:%M:%S'
    return logging_formatter

def get_logger(request, name="ot_api"):
    """
    Returns a logger with name set as given, and configured
    to the level given by the environment variable _LOGGING_LEVEL_ENVAR.
    """
#     package_dir = os.path.dirname(module_path)
#     config_filepath = os.path.join(package_dir, _LOGGING_CONFIG_FILE)
#     if os.path.exists(config_filepath):
#         try:
#             logging.config.fileConfig(config_filepath)
#             logger_set = True
#         except:
#             logger_set = False
    logger = logging.getLogger(name)
    if len(logger.handlers) == 0:
        if request is None:
            level = _get_logging_level(os.environ.get(_LOGGING_LEVEL_ENVAR))
            logging_formatter = _get_logging_formatter(os.environ.get(_LOGGING_FORMAT_ENVAR))
            logging_filepath = os.environ.get(_LOGGING_FILE_PATH_ENVAR)
        else:
            level_str, logging_format_name, logging_filepath = read_logging_config(request)
            logging_formatter = _get_logging_formatter(logging_format_name)
            level = _get_logging_level(level_str)

        logger.setLevel(level)
        if logging_filepath is not None:
            log_dir = os.path.split(logging_filepath)[0]
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            ch = logging.FileHandler(logging_filepath)
        else:
            ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(logging_formatter)
        logger.addHandler(ch)
    return logger
'''
def log_time_diff(log_obj, operation='', prev_time=None):
    '''If prev_time is not None, logs (at debug level) to
    log_obj the difference between now and the naive datetime
    object prev_time.
    `operation` is a string describing what events were timed.
    The current time is returned to allow for several
    calls with the form
       x = log_time_diff(_LOG, 'no op', x)
       foo()
       x = log_time_diff(_LOG, 'foo', x)
       bar()
       x = log_time_diff(_LOG, 'bar', x)
    '''
    n = datetime.now()
    if prev_time is not None:
        td = n - prev_time
        t = td.total_seconds()
        log_obj.debug('Timed operation "{o}" took {t:f} seconds'.format(o=operation, t=t))
    return n

def get_otindex_base_url(request):
    conf = get_conf_object(request)
    otindex_base_url = conf.get("apis", "otindex_base_url")
    return otindex_base_url

def get_oti_base_url(request):
    conf = get_conf_object(request)
    oti_base_url = conf.get("apis", "oti_base_url")
    if oti_base_url.startswith('//'):
        # Prepend scheme to a scheme-relative URL
        oti_base_url = "https:" + oti_base_url
    return oti_base_url

def get_oti_domain(request):
    oti_base = get_oti_base_url(request)
    s = oti_base.split('/')
    assert len(s) > 2
    return '/'.join(s[:3])

def get_collections_api_base_url(request):
    conf = get_conf_object(request)
    base_url = conf.get("apis", "collections_api_base_url")
    if base_url.startswith('//'):
        # Prepend scheme to a scheme-relative URL
        base_url = "https:" + base_url
    return base_url

def get_amendments_api_base_url(request):
    conf = get_conf_object(request)
    base_url = conf.get("apis", "amendments_api_base_url")
    if base_url.startswith('//'):
        # Prepend scheme to a scheme-relative URL
        base_url = "https:" + base_url
    return base_url

def get_favorites_api_base_url(request):
    conf = get_conf_object(request)
    base_url = conf.get("apis", "favorites_api_base_url")
    if base_url.startswith('//'):
        # Prepend scheme to a scheme-relative URL
        base_url = "http:" + base_url
    return base_url

def clear_matching_cache_keys(key_pattern):
    # emulate our regex-powered cache clearing, as used in web2py
    """
    # brute force method, will clear all Beaker caches
    for _cache in cache_managers.values():
        _cache.clear()
    """
    assert len(cache_managers) == 1
    # NB - code below may change if we use multiple caches/regions!
    active_cache = list(cache_managers.values())[0]
    ns_mgr = active_cache.namespace
    namespaces = ns_mgr.namespaces.dict
    """
    This yields specific namespaces in the active cache, and keys/values for each cached item, e.g. 
    {
      '/Users/jima/projects/opentree/phylesystem-api/phylesystem_api/phylesystem_api/views/default.py|fetch_and_cache': {
        b'pull-through v3/amendments/list_all': (1648487894.102585, 600, <Response at 0x10f75fc10 200 OK>),
        b'another key': (1648487894.102585, 600, <Response at 0x10f75fc10 200 OK>)
      },
      'another namespace': {
        b'first key': (...),
        b'second key': (...)
      }
    }
    """
    assert len(namespaces) == 1
    active_namespace = list(namespaces.values())[0]
    # NB - again, code may change if we use multiple namespaces here
    item_count_before = len(list(active_namespace.items()))
    """
    print("=== %d RAM cache keys BEFORE clearing: ===" % item_count_before)
    for k, v in active_namespace.items():
        print('{k} ===> {v}'.format(k=k,v=v))
    print("===")
    """
    #_LOG.debug("> clearing cached items matching [%s]" % key_pattern)

    matching_keys = []
    for k, v in active_namespace.items():
        if re.match(key_pattern, str(k)):
            matching_keys.append(k)
    for matching_key in matching_keys:
        del active_namespace[ matching_key ]

    """
    item_count_after = len(list(active_namespace.items()))
    print("=== %d RAM cache keys AFTER clearing: ===" % item_count_after)
    for k, v in active_namespace.items():
        print('{k} ===> {v}'.format(k,v))
    print("===")
    print("  %d items removed" % (item_count_before - item_count_after,))
    """

def raise_on_CORS_preflight(request):
    "A simple method for approving CORS preflight request"
    if request.method == 'OPTIONS':
        # NB - This is VERY welcoming, which is our current API posture!
        requested_methods = request.headers.get('Access-Control-Allow-Methods', None)
        requested_headers = request.headers.get('Access-Control-Allow-Headers', None)
        if requested_methods:
            request.response.headers['Access-Control-Allow-Methods'] = requested_methods
        if requested_headers:
            request.response.headers['Access-Control-Allow-Headers'] = requested_headers
        raise HTTPOk("CORS preflight!", headers=request.response.headers)

def raise_if_read_only():
    "Add this to any web view that is disabled in a read-only setup"
    if READ_ONLY_MODE:
        raise HTTPForbidden(json.dumps({"error": 1, "description": "phylesystem-api running in read-only mode"}))
    return True


def call_http_json(url,
                   verb='GET',
                   data=None,
                   headers=None):
    if headers is None:
        headers = {
            'content-type' : 'application/json',
            'accept' : 'application/json',
        }
    if data:
        resp = requests.request(verb,
                                url,
                                headers=headers,
                                data=json.dumps(data),
                                allow_redirects=True)
    else:
        resp = requests.request(verb, url, headers=headers, allow_redirects=True)
    resp.raise_for_status()
    return resp.status_code, resp.json()
    

def deferred_push_to_gh_call(request, resource_id, doc_type='nexson', **kwargs):
    raise_if_read_only()
    # _LOG = api_utils.get_logger(request, 'ot_api.default.v1')
    # Pass the resource_id in data, so that two-part collection IDs will be recognized
    # (else the second part will trigger an unwanted JSONP response from the push)
    url = compose_push_to_github_url(request, resource_id=None, doc_type=doc_type)
    auth_token = copy.copy(request.json_body.get('auth_token'))
    data = {'doc_type': doc_type, 'resource_id': resource_id}
    if auth_token is not None:
        data['auth_token'] = auth_token
    #call_http_json(url=url, verb='PUT', data=data)
    threading.Thread(target=call_http_json, args=(url, 'PUT', data,)).start()

def find_in_request(request, property_name, default_value=None, return_all_values=False):
    """Search JSON body (if any), then try GET/POST keys"""
    try:
        assert(isinstance(request, Request))
    except AssertionError:
        raise HTTPServerError(json.dumps({"error": 1, "description": 'request not provided in call to api_utils.find_in_request!'}))
    try:
        # recommended practice is all vars in the JSON body
        found_value = request.json_body.get(property_name)
    except:
        found_value = None
    if found_value is None:
        # sometimes we allow vars from the query-string or form values
        if return_all_values:
            # NB - request.params combines GET and POST into a shared MultiDict
            found_value = request.params.getall(property_name)
        else:
            # NB this returns None if default not specified!
            found_value = request.params.get(property_name, default_value)
    if found_value is None:
        return default_value
    return found_value



# Define a consistent cleaner to sanitize user input. We need a few
# tags and attributes that are common in our markdown but missing from the
# default Bleach whitelist.
import markdown
import re
import bleach
from bleach.sanitizer import Cleaner
# N.B. HTML comments are stripped by default. Non-allowed tags will appear
# "naked" in output, so we can identify any bad actors.
allowed_curation_comment_tags = ['p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'pre', 'code']  # any others?
ot_markdown_tags = list(set( bleach.sanitizer.ALLOWED_TAGS + allowed_curation_comment_tags))
# allow hyperlinks with target="_blank"
ot_markdown_attributes = {}
ot_markdown_attributes.update(bleach.sanitizer.ALLOWED_ATTRIBUTES)
ot_markdown_attributes['a'].append('target')
ot_cleaner = Cleaner(tags=ot_markdown_tags, attributes=ot_markdown_attributes)

def markdown_to_html(markdown_src='', open_links_in_new_window=False):
    extensions = ['mdx_linkify', ]
    try:  # coerce byte-string to Unicode
        markdown_src = markdown_src.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        pass
    html = markdown.markdown(markdown_src, extensions=extensions, )
    # NB - This is clumsy, but seems impossible to do with a second extension
    # like `markdown-link-attr-modifier`
    if open_links_in_new_window:
        html = re.sub(r' href=',
                      r' target="_blank" href=',
                      html)
    # scrub HTML output with bleach
    html = ot_cleaner.clean(html)
    try:  # coerce byte-string to Unicode
        html = html.decode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        pass
    return html

# another simple clean function to strip ALL tags (and entities from HTML
def remove_tags(markup):
    try:  # coerce Unicode to byte-string (required by ElementTree)
        markup = markup.encode('utf-8')
    except (UnicodeDecodeError, AttributeError):
        pass
    try:
        markup = u''.join(ElementTree.fromstring(markup).itertext())
    except ElementTree.ParseError:
        # if it won't parse (badly-formed XML/HTML, or plaintext), return unchanged
        pass
    # return value should be Unicode, not bytes
    markup = markup.decode('utf-8')
    return markup

