#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
study = '10'
SUBMIT_URI = DOMAIN + '/v1/study/' + study
data = {'output_nexml2json':'1.2'}
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          data=data,
                          expected_status=200,
                          return_bool_data=True)
d = r[1]['data']
c = d['nexml'].get('^ot:testCount', 0)
if isinstance(c, list):
    c = c[0]
c = c + 1
d['nexml']['^ot:testCount'] = c

if config('host', 'allowwrite', 'true') == 'false': sys.exit(0)

starting_commit_SHA = r[1]['sha']
data = { 'nexson' : d,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
r2 = test_http_json_method(SUBMIT_URI,
                           'PUT',
                           data=data,
                           expected_status=200,
                           return_bool_data=True)

PUSH_URI = DOMAIN + '/push/v1/' + study
r3 = test_http_json_method(PUSH_URI,
                           'PUT',
                           expected_status=200,
                           return_bool_data=True)
print r3
