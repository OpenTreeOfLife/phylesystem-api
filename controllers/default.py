import os
import time
from gluon.tools import Auth

def index():
    def GET():
        return locals()

@request.restful()
def api():
    response.view = 'generic.json'
    def GET(resource,resource_id):
        if not resource=='study': raise HTTP(400)
        # return the correct nexson of study_id
        return _get_nexson(resource_id)

    def POST(resource,resource_id, **kwargs):
        if not resource=='study': raise HTTP(400, 'resource != study')

        if resource_id < 0 : raise HTTP(400, 'invalid resource_id: must be a postive integer')

        # TODO: validate
        nexson       = kwargs.get('nexson','{}')
        author_name  = kwargs.get('author_name','')
        author_email = kwargs.get('author_email','')

        # overwrite the nexson of study_id with the POSTed data
        # 1) verify that it is valid json
        # 2) Update local treenexus git submodule at ./treenexus
        # 3) See if the hash of the current value of the file matches the hash of the POSTed data. If so, do nothing and return successfully.
        # 4) If not, overwrite the correct nexson file on disk
        # 5) Make a git commit with the updated nexson (add as much automated metadata to the commit message as possible)
        # 6) return successfully

        return dict()
    return locals()

def _get_nexson(study_id):

    this_dir = os.path.dirname(os.path.abspath(__file__))

    try:
        filename    = this_dir + "/../treenexus/study/" + study_id + "/" + study_id + ".json"
        nexson_file = open(filename,'r')
    except IOError:
        return '{}'

    return nexson_file.readlines()
