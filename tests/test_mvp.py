from nose       import with_setup
from nose.tools import *

import requests
import os

def test_basic_api_get():
    # Currently the URL http://localhost:8000/welcome/default/api/study/10.json works

    protocol = 'http://'
    host     = '127.0.0.1'
    port     = os.environ['OTOL_API_PORT'] or "8000"
    prefix   = "/welcome/default/api"
    url      = protocol + host + ":" + port + prefix + '/study/10.json'

    # ask the API for the study 10 NexSON
    r        = requests.get(url)

    eq_(r.status_code, requests.codes.ok, url + " returns a successful status code")

    expected_content_type = 'application/json'
    eq_(r.headers.get('content-type'), expected_content_type, r.headers.get('content-type') + "== " + expected_content_type)

    try:
        nexson = r.json()
        assert 1, "Valid JSON"
    except:
        assert 0, "Invalid JSON : "

    assert len(str(nexson)) > 3, "Returned NexSON is non-empty "

def test_basic_api_post():
    protocol = 'http://'
    host     = '127.0.0.1'
    port     = os.environ['OTOL_API_PORT'] or "8000"
    prefix   = "/welcome/default/api"
    url      = protocol + host + ":" + port + prefix + '/study/10.json'

    api_key  = 'deadbeef'
    nexson   = '{ "foo": "bar" }'

    # ask the API to overwrite the NexSON for study 10
    payload = {'key': api_key , 'nexson': nexson}
    r        = requests.post(url, data=payload)

    eq_(r.status_code, requests.codes.ok, url + " returns a successful status code")

    expected_content_type = 'application/json'
    eq_(r.headers.get('content-type'), expected_content_type, r.headers.get('content-type') + "== " + expected_content_type)

    try:
        returned_nexson = str(r.json())
        assert 1, "Valid JSON"
    except:
        assert 0, "Invalid JSON : " + nexson

    assert len(str(returned_nexson)) > 3, "Returned NexSON is non-empty:"
