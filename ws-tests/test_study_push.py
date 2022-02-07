#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit
DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
study = '10'
SUBMIT_URI = DOMAIN + '/v3/study/' + study
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
starting_commit_SHA = r[1]['sha']
data = { 'nexson' : d,
         'auth_token': auth_token,
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
print(r3)
