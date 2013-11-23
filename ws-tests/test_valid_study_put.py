#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import codecs
import json
import sys

DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/1003'
inpf = codecs.open('../nexson-validator/tests/single/input/1003.json', 'rU', encoding='utf-8')
n = json.load(inpf)
data = { 'nexson' : n,
         'auth_token': 'bogus_token'
}
if test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200):
    sys.exit(0)
sys.exit(1)
