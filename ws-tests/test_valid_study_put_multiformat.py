#!/usr/bin/env python
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit
from peyotl import convert_nexson_format
import datetime
import codecs
import json
import sys
import os
DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
study_id = 12
URL = DOMAIN + '/v3/study/%s' % study_id
r = test_http_json_method(URL,
                          'GET',
                          expected_status=200,
                          return_bool_data=True,
                          headers={'content-type':'text/plain', 'accept':'text/plain'},
                          is_json=True)
if not r[0]:
    sys.exit(1)
starting_commit_SHA = r[1]['branch2sha']['master']
SUBMIT_URI = DOMAIN + '/v3/study/%s' % study_id
fn = 'data/{s}.json'.format(s=study_id)
inpf = codecs.open(fn, 'rU', encoding='utf-8')
n = json.load(inpf)
# refresh a timestamp so that the test generates a commit
m = n['nexml']['meta']
short_list = [i for i in m if i.get('@property') == 'bogus_timestamp']
if short_list:
    el = short_list[0]
else:
    el = {'@property': 'bogus_timestamp', '@xsi:type': 'nex:LiteralMeta'}
    m.append(el)
el['$'] = datetime.datetime.utcnow().isoformat()
n = convert_nexson_format(n, '1.2')
data = { 'nexson' : n,
         'auth_token': auth_token,
         'starting_commit_SHA': starting_commit_SHA,
}
if test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200):
    sys.exit(0)
sys.exit(1)
