#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import datetime
import codecs
import json
import sys
import os

DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/'
inpf = codecs.open('data/10.json', 'rU', encoding='utf-8')
n = json.load(inpf)
# refresh a timestamp so that the test generates a commit
m = n['nexml']['^bogus_timestamp'] = datetime.datetime.utcnow().isoformat()

data = { 'nexson' : n,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'cc0_agreement' : 'true',
}

r = test_http_json_method(SUBMIT_URI,
                         'POST',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)
if not r[0]:
    sys.exit(1)
resp = r[1]
starting_commit_SHA = resp['sha']
c_id = resp['resource_id']
print c_id

DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/%s' % c_id
data = {
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
         'commit_msg': 'Test study deletion with commit message',
}
r = test_http_json_method(SUBMIT_URI, 'DELETE', data=data, expected_status=200, return_bool_data=True)
if not r[0]:
    sys.exit(1)
resp = r[1]
assert resp['merge_needed'] == False
