import os
import time
import json
import hashlib
import github_client
from pprint import pprint
from github import Github

def index():
    def GET():
        return locals()

@request.restful()
def api():
    response.view = 'generic.json'

    def GET(resource,resource_id,jsoncallback=None,callback=None,_=None,**kwargs):
        if not resource=='study': raise HTTP(400, 'resource != study [GET]')

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
            # TODO: use readlines() in some way, to handle humongous files?
            return dict(FULL_RESPONSE=github_client.fetch_study(resource_id, auth_token))
        except Exception, e:
            return 'ERROR fetching study:\n%s' % e

    def POST(resource, resource_id, **kwargs):
        # support JSONP request from another domain
        if kwargs.get('jsoncallback',None) or kwargs.get('callback',None):
            response.view = 'generic.jsonp'

        if not resource=='study': raise HTTP(400, 'resource != study')

        if resource_id < 0 : raise HTTP(400, 'invalid resource_id: must be a postive integer')

        author_name  = kwargs.get('author_name','')
        author_email = kwargs.get('author_email','')
        # this is the GitHub API auth-token for a logged-in curator
        auth_token   = kwargs.get('auth_token','')

        if not auth_token:
            raise HTTP(400,"You must authenticate to before updating via the OTOL API")

        # Connect to the Github v3 API via with this OAuth token
        gh = Github(oauth_token)

        try:
            nexson        = json.loads( kwargs.get('nexson','{}') )
        except:
            raise HTTP(400, 'NexSON must be valid JSON')

        # sort the keys of the POSTed NexSON and indent 4 spaces
        nexson = json.dumps(nexson, sort_keys=True, indent=4)

        _update_treenexus()

        # We compare sha1's instead of the actual data to reduce memory use
        # when comparing large studies
        posted_nexson_sha1 = hashlib.sha1(nexson).hexdigest()
        nexson_sha1        = hashlib.sha1( _get_nexson(resource_id, auth_token) ).hexdigest()

        # the POSTed data is the same as what we have on disk, do nothing and return successfully
        if posted_nexson_sha1 == nexson_sha1:
            return { error: 0, description: "success" };
        else:
            # we have new data
            # TODO: Use http://jacquev6.github.io/PyGithub/github_objects/Repository.html#github.Repository.Repository.create_git_commit
            return dict()
    return locals()

def _update_treenexus():
    """Update the treenexus git submodule"""
    # submodule update must be run from the top-level dir of our repo
    rc = os.system("cd ..; git submodule update")
    if rc:
        raise HTTP(400,"Unable to update local treenexus.git")

def _study_id_to_filename(study_id):
    """Return the filename of a given study_id"""
    this_dir  = os.path.dirname(os.path.abspath(__file__))
    filename  = this_dir + "/../treenexus/study/" + study_id + "/" + study_id + ".json"
    return filename

