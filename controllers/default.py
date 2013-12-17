import os, sys
import time
import json
import hashlib
import github
from github import Github, BadCredentialsException
from pprint import pprint
from gitdata import GitData
from ConfigParser import SafeConfigParser
from locket import LockError

# NexSON validation
from nexson_validator import WarningCodes, create_validation_nexson, prepare_annotation, add_or_replace_annotation

@request.restful()
def v1():
    "The OpenTree API v1"
    response.view = 'generic.json'

    # CORS support for cross-domain API requests (from anywhere)
    response.headers['Access-Control-Allow-Origin'] = "*"
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = 86400  # cache for a day

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
    git_ssh     = conf.get("apis", "git_ssh")
    pkey        = conf.get("apis", "pkey")
    git_env     = {"GIT_SSH": git_ssh, "PKEY": pkey}

    def __validate(nexson):
        '''Returns three objects:
            an annotation dict (NexSON formmatted), 
            the validation_log object created when NexSON validation was performed, and
            the object of class NexSON which was created from nexson. This object will
                alias parts of the nexson dict that is passed in as an argument.
        '''
        # stub function for hooking into NexSON validation
        codes_to_skip = [WarningCodes.UNVALIDATED_ANNOTATION]
        script_name = 'api.opentreeoflife.org/validate' # TODO
        validation_log, nexson_obj = create_validation_nexson(nexson, codes_to_skip, retain_deprecated=True)
        annotation = prepare_annotation(validation_log,
                                        author_name=script_name,
                                        annotation_label="Open Tree NexSON validation")
        return annotation, validation_log, nexson_obj

    def GET(resource,resource_id,jsoncallback=None,callback=None,_=None,**kwargs):
        "OpenTree API methods relating to reading"
        valid_resources = ('study')

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
        try:
            gd = GitData(repo=repo_path)
            study_nexson = gd.fetch_study(resource_id)
            return dict(FULL_RESPONSE=study_nexson)
        except Exception, e:
            return 'ERROR fetching study:\n%s' % e

    def POST(resource, resource_id=None, _method='POST', **kwargs):
        "OTOL API methods relating to creating (and importing) resources"

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
        dryad_DOI = kwargs.get('dryad_DOI', '')
        import_option = kwargs.get('import_option', '')

        #TODO, need to make this spawn a thread to do the second commit rather than block
        block_until_annotation_commit = True

        (gh, author_name, author_email) = authenticate(**kwargs)
        nexson, annotation, validation_log, rich_nexson = validate_and_normalize_nexson(**kwargs)

        gd = GitData(repo=repo_path)

        # studies created by the OpenTree API start with o,
        # so they don't conflict with new study id's from other sources
        new_resource_id = "o%d" % (gd.newest_study_id() + 1)

        unadulterated_content_commit = do_commit(gd, gh, nexson, author_name, author_email, new_resource_id)
        if unadulterated_content_commit['error'] != 0:
            raise HTTP(400, json.dumps(unadulterated_content_commit))
        if block_until_annotation_commit:
            # add the annotation and commit the resulting blob...
            add_or_replace_annotation(rich_nexson._raw, annotation)
            nexson = json.dumps(rich_nexson._raw, sort_keys=True, indent=0)
            annotated_commit = do_commit(gd, gh, nexson, author_name, author_email, new_resource_id)
            if annotated_commit['error'] != 0:
                raise HTTP(400, json.dumps(annotated_commit))
            return annotated_commit
        else:
            return unadulterated_content_commit

    def validate_and_normalize_nexson(**kwargs):
        """A wrapper around __validate() which also sorts JSON keys and checks for invalid JSON"""
        try:
            nexson = kwargs.get('nexson', {})
            if not isinstance(nexson, dict):
                nexson = json.loads(nexson)
        except:
            raise HTTP(400, json.dumps({"error": 1, "description": 'NexSON must be valid JSON'}))

        annotation, validation_log, rich_nexson = __validate(nexson)
        if validation_log.errors:
            raise HTTP(400, json.dumps(annotation))

        # sort the keys of the POSTed NexSON and indent 0 spaces
        nexson = json.dumps(nexson, sort_keys=True, indent=0)

        return nexson, annotation, validation_log, rich_nexson

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

    def PUT(resource, resource_id, **kwargs):
        "OTOL API methods relating to updating existing resources"
        #TODO, need to make this spawn a thread to do the second commit rather than block
        block_until_annotation_commit = True
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'
        if not resource=='study': raise HTTP(400, 'resource != study')

        gh, author_name, author_email = authenticate(**kwargs)

        nexson, annotation, validation_log, rich_nexson = validate_and_normalize_nexson(**kwargs)

        gd = GitData(repo=repo_path)

        # We compare sha1's instead of the actual data to reduce memory use
        # when comparing large studies
        posted_nexson_sha1 = hashlib.sha1(nexson).hexdigest()
        nexson_sha1        = hashlib.sha1( gd.fetch_study(resource_id) ).hexdigest()

        # the POSTed data is the same as what we currently have, do nothing and return successfully
        if posted_nexson_sha1 == nexson_sha1:
            return { "error": 0, "description": "success, nothing to update" };
        else:

            unadulterated_content_commit = do_commit(gd, gh, nexson, author_name, author_email, resource_id)
            if unadulterated_content_commit['error'] != 0:
                raise HTTP(400, json.dumps(unadulterated_content_commit))
            if block_until_annotation_commit:
                # add the annotation and commit the resulting blob...
                add_or_replace_annotation(rich_nexson._raw, annotation)
                nexson = json.dumps(rich_nexson._raw, sort_keys=True, indent=0)
                annotated_commit = do_commit(gd, gh, nexson, author_name, author_email, resource_id)
                if annotated_commit['error'] != 0:
                    raise HTTP(400, json.dumps(annotated_commit))
                return annotated_commit
            else:
                return unadulterated_content_commit

    def do_commit(gd, gh, file_content, author_name, author_email, resource_id):
        """Actually make a local Git commit and push it to our remote
        """
        author  = "%s <%s>" % (author_name, author_email)

        branch_name  = "%s_study_%s" % (gh.get_user().login, resource_id)

        try:
            gd.acquire_lock()
        except LockError, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not acquire lock to write to study #%s" % resource_id
            }))

        try:
            new_sha = gd.write_study(resource_id,file_content,branch_name,author)
        except:
            e = sys.exc_info()[0]

            gd.release_lock()

            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not write to study #%s due to %s Exception" % (resource_id, e)
            }))

        try:
            # actually push the changes to Github
            gd.push(repo_remote, env=git_env)
        except:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not push deletion of study #%s" % resource_id
            }))
        finally:
            gd.release_lock()

        # What other useful information should be returned on a successful write?
        return {
            "error": 0,
            "branch_name": branch_name,
            "description": "Updated study #%s" % resource_id,
            "sha":  new_sha
        }

    def DELETE(resource, resource_id=None, **kwargs):
        "OTOL API methods relating to deleting existing resources"
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'

        if not resource=='study': raise HTTP(400, 'resource != study')

        (gh, author_name, author_email) = authenticate(**kwargs)

        author       = "%s <%s>" % (author_name, author_email)

        branch_name  = "%s_study_%s" % (gh.get_user().login, resource_id)

        gd = GitData(repo=repo_path)

        try:
            gd.acquire_lock()
        except LockError, e:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not acquire lock to delete the study #%s" % resource_id
            }))

        try:
            new_sha = gd.remove_study(resource_id, branch_name, author)
        except:
            gd.release_lock()

            e = sys.exc_info()[0]
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not remove study #%s due to %s Exception" % (resource_id, e)
            }))

        try:
            # actually push the changes to Github
            gd.push(repo_remote, env=git_env)
        except:
            raise HTTP(400, json.dumps({
                "error": 1,
                "description": "Could not push deletion of study #%s" % resource_id
            }))
        finally:
            gd.release_lock()

        return {
            "error": 0,
            "branch_name": branch_name,
            "description": "Deleted study #%s" % resource_id,
            "sha":  new_sha
        }

    def OPTIONS(args, **kwargs):
        "A simple method for approving CORS preflight request"
        if request.env.http_access_control_request_method:
             response.headers['Access-Control-Allow-Methods'] = request.env.http_access_control_request_method
        if request.env.http_access_control_request_headers:
             response.headers['Access-Control-Allow-Headers'] = request.env.http_access_control_request_headers
        raise HTTP(200)

    return locals()
