import requests
import simplejson as json


class OTISearch(object):
    def __init__(self, api_base_url):
        self.api_base_url = api_base_url

    def do_search(self, kind, key, value):
        kind_to_oti_url = {
            "tree": "v3/studies/find_trees",
            "node": "v3/studies/find_nodes",  # CURRENTLY UNSUPPORTED in v3 APIs
            "study": "v3/studies/find_studies",
        }

        headers = {
            "content-type": "application/json",
            "accept": "application/json",
        }
        search_url = self.api_base_url + kind_to_oti_url[kind]
        data = {"property": key, "value": value}

        r = requests.post(
            search_url, headers=headers, data=json.dumps(data), allow_redirects=True
        )
        try:
            response = r.json()
        except:
            return json.dumps({"error": 1})

        return response
