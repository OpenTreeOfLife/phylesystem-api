#!/usr/bin/env python
from opentreetesting import test_http_json_method, config, exit_if_api_is_readonly
import datetime
import codecs
import json
import sys
import os

DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/'
inpf = codecs.open('data/10.json', 'rU', encoding='utf-8')
n = json.load(inpf)
# refresh a timestamp so that the test generates a commit
m = n['nexml']['^bogus_timestamp'] = datetime.datetime.utcnow().isoformat()

exit_if_api_is_readonly(__file__)

data = { 'nexson' : n,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'cc0_agreement' : 'true',
         'import_method' : 'import-method-POST',
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
SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/%s' % c_id
data = {
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
r = test_http_json_method(SUBMIT_URI, 'DELETE', data=data, expected_status=200, return_bool_data=True)
if not r[0]:
    sys.exit(1)
resp = r[1]
assert resp['merge_needed'] == False
