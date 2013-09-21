from nose       import with_setup
from nose.tools import *

import requests

def test_basic_api_call():
    protocol = 'http://'
    host     = 'localhost'
    port     = 8000
    url      = protocol + host + ":" + port + '/v1/study/10.json'

    # ask the API for the NexSON for study 10
    r        = requests.get(url)

    ok_(r.status_code == requests.codes.ok, url + " returns a successful status code")

    json = r.json()
