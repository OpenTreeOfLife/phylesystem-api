#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config, exit_if_api_is_readonly
DOMAIN = config('host', 'apihost')
study = '10'
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/' + study
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

exit_if_api_is_readonly(__file__)

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

PUSH_URI = DOMAIN + '/phylesystem/push/v1/' + study
r3 = test_http_json_method(PUSH_URI,
                           'PUT',
                           expected_status=200,
                           return_bool_data=True)
print r3
