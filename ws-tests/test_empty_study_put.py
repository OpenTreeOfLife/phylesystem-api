#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit
DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/pg_99'
data = { 'auth_token': auth_token}
if test_http_json_method(SUBMIT_URI, 'PUT', data, expected_status=400): #expected_response={}):
    sys.exit(0)
sys.exit(1)
