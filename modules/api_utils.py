from ConfigParser import SafeConfigParser
from github import Github, BadCredentialsException
from datetime import datetime
import logging
import os
import json


# this allows us to raise HTTP(...)
from gluon import *

def read_config(request):
    app_name = "api"
    conf = SafeConfigParser(allow_no_value=True)
    localconfig_filename = "%s/applications/%s/private/localconfig" % (request.env.web2py_path, app_name)

    if os.path.isfile(localconfig_filename):
        conf.readfp(open(localconfig_filename))
    else:
        filename = "%s/applications/%s/private/config" % (request.env.web2py_path, app_name)
        conf.readfp(open(filename))

    repo_path   = conf.get("apis","repo_path")
    repo_remote = conf.get("apis", "repo_remote")
    try:
        git_ssh     = conf.get("apis", "git_ssh")
    except:
        git_ssh = 'ssh'
    try:
        pkey        = conf.get("apis", "pkey")
    except:
        pkey = None

    return repo_path, repo_remote, git_ssh, pkey

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

    try:
        gh_user.login
    except BadCredentialsException:
        raise HTTP(400,json.dumps({
            "error": 1,
            "description":"You have provided an invalid or expired authentication token"
        }))

    author_name  = kwargs.get('author_name','')
    author_email = kwargs.get('author_email','')

    # use the Github Oauth token to get a name/email if not specified
    # we don't provide these as default values above because they would
    # generate API calls regardless of author_name/author_email being specifed

    if not author_name:
        author_name = gh_user.name
    if not author_email:
        author_email = gh_user.email

    return gh, author_name, author_email


_LOGGING_LEVEL_ENVAR="OT_API_LOGGING_LEVEL"
_LOGGING_FORMAT_ENVAR="OT_API_LOGGING_FORMAT"

def _get_logging_level():
    if _LOGGING_LEVEL_ENVAR in os.environ:
        if os.environ[_LOGGING_LEVEL_ENVAR].upper() == "NOTSET":
            level = logging.NOTSET
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "DEBUG":
            level = logging.DEBUG
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "INFO":
            level = logging.INFO
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "WARNING":
            level = logging.WARNING
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "ERROR":
            level = logging.ERROR
        elif os.environ[_LOGGING_LEVEL_ENVAR].upper() == "CRITICAL":
            level = logging.CRITICAL
        else:
            level = logging.NOTSET
    else:
        level = logging.NOTSET
    return level

def get_logger(name="ot_api"):
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
        level = _get_logging_level()
        rich_formatter = logging.Formatter("[%(asctime)s] %(filename)s (%(lineno)d): %(levelname) 8s: %(message)s")
        simple_formatter = logging.Formatter("%(levelname) 8s: %(message)s")
        raw_formatter = logging.Formatter("%(message)s")
        default_formatter = None
        logging_formatter = default_formatter
        if _LOGGING_FORMAT_ENVAR in os.environ:
            if os.environ[_LOGGING_FORMAT_ENVAR].upper() == "RICH":
                logging_formatter = rich_formatter
            elif os.environ[_LOGGING_FORMAT_ENVAR].upper() == "SIMPLE":
                logging_formatter = simple_formatter
            elif os.environ[_LOGGING_FORMAT_ENVAR].upper() == "NONE":
                logging_formatter = None
            else:
                logging_formatter = default_formatter
        else:
            logging_formatter = default_formatter
        if logging_formatter is not None:
            logging_formatter.datefmt='%H:%M:%S'
        logger.setLevel(level)
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

