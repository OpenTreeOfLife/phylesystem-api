import os

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
    def POST(resource,resource_id):
        if not resource=='study': raise HTTP(400)
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

    # the internal file structure will change soon to study/study_id/study_id-N.json, where N=0,1,2,3...
    try:
        filename    = this_dir + "/../treenexus/study/0/" + study_id + ".json"
        nexson_file = open(filename,'r')
    except IOError:
        return '{}'

    return nexson_file.readlines()
