from nose       import with_setup
from nose.tools import *

import requests

def test_basic_api_get():
    protocol = 'http://'
    host     = 'localhost'
    port     = "8000"
    url      = protocol + host + ":" + port + '/v1/study/10.json'

    # ask the API for the study 10 NexSON
    r        = requests.get(url)

    eq_(r.status_code, requests.codes.ok, url + " returns a successful status code")

    eq_(r.headers.get('content-type'), 'application/json', url + "content-type is application/json")

    nexson = r.json()

    assert len(json) > 3, "Returned NexSON is non-empty"

def test_basic_api_post():
    protocol = 'http://'
    host     = 'localhost'
    port     = "8000"
    url      = protocol + host + ":" + port + '/v1/study/10.json'

    api_key  = 'deadbeef'
    nexson   = '{ "foo": "bar" }'

    # ask the API to overwrite the NexSON for study 10
    payload = {'key': api_key , 'nexson': nexson}
    r        = requests.post(url, data=payload)

    eq_(r.status_code, requests.codes.ok, url + " returns a successful status code")

    eq_(r.headers.get('content-type'), 'application/json', url + "content-type is application/json")

    json = r.json()

    assert len(json) > 3, "Returned NexSON is non-empty"
