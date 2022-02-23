#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
CONTROLLER = DOMAIN + '/v3/studies'
SUBMIT_URI = CONTROLLER + '/find_studies'
p = {'verbose': True,
     'property': 'ot:studyPublication',
     'value': 'http://dx.doi.org/10.1600/036364408785679851',}
# DOI was formerly 10.3732/ajb.94.11.1860
r = test_http_json_method(SUBMIT_URI,
                          'POST',
                          data=p,
                          expected_status=200,
                          return_bool_data=True)
assert r[0] is True
assert len(r[1]) > 0
assert 'ot:studyId' in list(r[1][0].keys())
