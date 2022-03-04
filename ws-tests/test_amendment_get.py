#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
# ask for a known-good amendment
SUBMIT_URI = DOMAIN + '/v3/amendment/additions-10000004-10000005'
# NB - This poorly-named methd returns a list of just their IDs
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          expected_status=200,
                          return_bool_data=True)
if not r[0]:
    sys.exit(1)
assert len(r) == 2
assert isinstance(r[1], dict)
