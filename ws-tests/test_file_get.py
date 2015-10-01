#!/usr/bin/env python
import sys
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
if '/api.opentree' in DOMAIN:
    study = 'ot_134'
elif '/devapi.opentree' in DOMAIN:
    study = 'tt_23'
else:
    study = 'pg_90'
# '/file' means get list of supplementary files
SUBMIT_URI = '{d}/phylesystem/v1/study/{s}/file'.format(d=DOMAIN, s=study)
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          expected_status=200,
                          return_bool_data=True,
                          is_json=True)
if r[0]:
    fid = r[1][0]['id']
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
if not r[0]:
    sys.exit(1)
