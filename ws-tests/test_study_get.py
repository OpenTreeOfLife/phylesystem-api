#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v3/study/10'
data = {'output_nexml2json':'1.2'}
if test_http_json_method(SUBMIT_URI, 'GET', data=data, expected_status=200):
    sys.exit(0)
sys.exit(1)
