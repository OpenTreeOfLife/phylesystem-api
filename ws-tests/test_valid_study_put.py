#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import datetime
import codecs
import json
import sys
import os

# this makes it easier to test concurrent pushes to different branches
DOMAIN = config('host', 'apihost')
study_id = '9'
SUBMIT_URI = DOMAIN + '/v1/study/' + study_id
data = {'output_nexml2json':'0.0.0'}
r = test_http_json_method(SUBMIT_URI, 'GET', data=data, expected_status=200, return_bool_data=True)
if not r[0]:
    sys.exit(0)
resp = r[1]
starting_commit_SHA = resp['sha']
SUBMIT_URI = DOMAIN + '/v1/study/{s}'.format(s=study_id)
n = resp['data']
# refresh a timestamp so that the test generates a commit
m = n['nexml']['meta']
short_list = [i for i in m if i.get('@property') == 'bogus_timestamp']
if short_list:
    el = short_list[0]
else:
    el = {'@property': 'bogus_timestamp', '@xsi:type': 'nex:LiteralMeta'}
    m.append(el)
el['$'] = datetime.datetime.utcnow().isoformat()

data = { 'nexson' : n,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
r = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)
if not r[0]:
    sys.exit(0)

print r[1]