#!/usr/bin/env python
import sys
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/9'
data = { 'auth_token': 'bogus_token'
}
if test_http_json_method(SUBMIT_URI, 'PUT', data, expected_status=400): #expected_response={}):
    sys.exit(0)
sys.exit(1)
