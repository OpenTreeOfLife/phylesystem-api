from ConfigParser import SafeConfigParser
from peyotl.phylesystem import Phylesystem
from github import Github, BadCredentialsException
from datetime import datetime
import logging
import os
import json

def compose_push_to_github_url(request, resource_id):
    if resource_id is None:
        return '{p}://{d}/{a}/push/v1'.format(p=request.env.wsgi_url_scheme,
                                              d=request.env.http_host,
                                              a=request.application)
    return '{p}://{d}/{a}/push/v1/{r}'.format(p=request.env.wsgi_url_scheme,
                                           d=request.env.http_host,
                                           a=request.application,
                                           r=resource_id)

# this allows us to raise HTTP(...)
from gluon import *
_PHYLESYSTEM = None
def get_phylesystem(request):
    global _PHYLESYSTEM
    if _PHYLESYSTEM is not None:
        return _PHYLESYSTEM
    from gitdata import GitData
    repo_parent, repo_remote, git_ssh, pkey, git_hub_remote = read_config(request)
    push_mirror = os.path.join(repo_parent, 'mirror')
    pmi = {
        'parent_dir': push_mirror,
        'remote_map': {
            'GitHubRemote': git_hub_remote,
            },
        }
    mirror_info = {'push':pmi}
    _PHYLESYSTEM = Phylesystem(repos_par=repo_parent,
                               git_ssh=git_ssh,
                               pkey=pkey,
                               git_action_class=GitData,
                               mirror_info=mirror_info)
    _LOG = get_logger(request, 'ot_api')
    _LOG.debug('repo_nexml2json = {}'.format(_PHYLESYSTEM.repo_nexml2json))
    return _PHYLESYSTEM

def read_config(request):
    app_name = "api"
    conf = SafeConfigParser(allow_no_value=True)
    localconfig_filename = "%s/applications/%s/private/localconfig" % (request.env.web2py_path, app_name)

    if os.path.isfile(localconfig_filename):
        conf.readfp(open(localconfig_filename))
    else:
        filename = "%s/applications/%s/private/config" % (request.env.web2py_path, app_name)
        conf.readfp(open(filename))

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
    return repo_parent, repo_remote, git_ssh, pkey, git_hub_remote

def read_logging_config(request):
    app_name = "api"
    conf = SafeConfigParser(allow_no_value=True)
    localconfig_filename = "%s/applications/%s/private/localconfig" % (request.env.web2py_path, app_name)

    if os.path.isfile(localconfig_filename):
        conf.readfp(open(localconfig_filename))
    else:
        filename = "%s/applications/%s/private/config" % (request.env.web2py_path, app_name)
        conf.readfp(open(filename))
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

def authenticate(**kwargs):
    """Verify that we received a valid Github authentication token

    This method takes a dict of keyword arguments and optionally
    over-rides the author_name and author_email associated with the
    given token, if they are present.

    Returns a PyGithub object, author name and author email.

    This method will return HTTP 400 if the auth token is not present
    or if it is not valid, i.e. if PyGithub throws a BadCredentialsException.

    """
    # this is the GitHub API auth-token for a logged-in curator
    auth_token   = kwargs.get('auth_token','')

    if not auth_token:
        raise HTTP(400,json.dumps({
            "error": 1,
            "description":"You must provide an auth_token to authenticate to the OpenTree API"
        }))
    gh           = Github(auth_token)
    gh_user      = gh.get_user()
    auth_info = {}
    try:
        auth_info['login'] = gh_user.login
    except BadCredentialsException:
        raise HTTP(400,json.dumps({
            "error": 1,
            "description":"You have provided an invalid or expired authentication token"
        }))

    auth_info['name'] = kwargs.get('author_name')
    auth_info['email'] = kwargs.get('author_email')

    # use the Github Oauth token to get a name/email if not specified
    # we don't provide these as default values above because they would
    # generate API calls regardless of author_name/author_email being specifed

    if auth_info['name'] is None:
        auth_info['name'] = gh_user.name
    if auth_info['email'] is None:
        auth_info['email']= gh_user.email
    return auth_info


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
    if not hasattr(logger, 'is_configured'):
        logger.is_configured = False
    if not logger.is_configured:
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
        logger.is_configured = True
    return logger

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

