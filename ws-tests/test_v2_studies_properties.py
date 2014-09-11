#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
CONTROLLER = DOMAIN + '/studies'
SUBMIT_URI = CONTROLLER + '/properties'
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          expected_status=200,
                          return_bool_data=True)
assert r[0] is True
k = r[1].keys()
assert 'study_properties' in k
assert isinstance(r[1]['tree_properties'], list)
