#!/usr/bin/env python
import sys
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
if '/api.opentree' in DOMAIN:
    study = 'ot_134'
else:
    study = 'pg_90'
SUBMIT_URI = '{d}/v1/study/{s}/file'.format(d=DOMAIN, s=study)
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          expected_status=200,
                          return_bool_data=True,
                          is_json=True)
if r[0]:
    fid = r[1][0]['@id']
    print fid
else:
    sys.exit(1)
NEW_URL = SUBMIT_URI + '/bogusid'
x = test_http_json_method(NEW_URL, 'GET', expected_status=404)
NEW_URL = SUBMIT_URI + '/' + fid
r = test_http_json_method(NEW_URL,
                          'GET',
                          expected_status=200,
                          return_bool_data=True,
                          headers={'content-type':'text/plain', 'accept':'text/plain'},
                          is_json=False)
if r[0]:
    print r[1]
else:
    sys.exit(1)
