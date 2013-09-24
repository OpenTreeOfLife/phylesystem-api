def index():
    def GET():
        return locals()

@request.restful()
def api():
    response.view = 'generic.json'
    def GET(resource,resource_id):
        if not resource=='study': raise HTTP(400)
        # return the correct nexson of study_id
        return dict()
    def POST(resource,resource_id):
        if not resource=='study': raise HTTP(400)
        # overwrite the nexson of study_id with the POSTed data
        # 1) verify that it is valid json
        # 2) Update local treenexus git repo at ../treenexus
        # 3) See if the hash of the current value of the file matches the hash of the POSTed data. If so, do nothing and return successfully.
        # 4) If not, overwrite the correct nexson file on disk
        # 5) Make a git commit with the updated nexson (add as much automated metadata to the commit message as possible)
        # 6) return successfully

        return dict()
    return locals()
