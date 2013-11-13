import requests
import simplejson as json

class GithubSearch(object):
    def __init__(self):
        self.api_url = "https://api.github.com/search/code?q="
        self.repo    = "OpenTreeOfLife/treenexus"
    def search(self,term):
        search_url = "%s+repo:%s" % (self.api_url, self.repo)
        r = requests.get(search_url)
        if r.ok:
            search_json = json.loads(r.text or r.content)
