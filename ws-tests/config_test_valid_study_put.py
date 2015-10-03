#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import datetime
import codecs
import json
import sys
import os

# this makes it easier to test concurrent pushes to different branches
DOMAIN = config('host', 'apihost')
study_id = '10'
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/' + study_id
data = {'output_nexml2json':'1.0.0'}
r = test_http_json_method(SUBMIT_URI, 'GET', data=data, expected_status=200, return_bool_data=True)
if not r[0]:
    sys.exit(0)
resp = r[1]
starting_commit_SHA = resp['sha']
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/{s}'.format(s=study_id)
n = resp['data']
# refresh a timestamp so that the test generates a commit
m = n['nexml']['^bogus_timestamp'] = datetime.datetime.utcnow().isoformat()

#from peyotl import write_as_json
#write_as_json(n, '9-0.0.0.json')
data = { 'nexson' : n,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
r = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=400,
                         return_bool_data=True)
if not r[0]:
    sys.exit(0)

print r[1]
