#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
CONTROLLER = DOMAIN + '/studies'
SUBMIT_URI = CONTROLLER + '/find_trees'
p = {'verbose': True,
     'property': 'ot:ottId',
     'value': '770315'}
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          data=p,
                          expected_status=200,
                          return_bool_data=True)
assert r[0] is True
assert len(r[1]) > 0
assert 'ot:studyId' in r[1][0]
