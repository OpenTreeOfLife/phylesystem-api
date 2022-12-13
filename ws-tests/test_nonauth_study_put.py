#!/usr/bin/env python
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit
import datetime
import codecs
import json
import sys
import os
DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
study_id = 12
SUBMIT_URI = DOMAIN + '/v3/study/{s}'.format(s=study_id)
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

data = { 'nexson' : n,
         'auth_token': 'bogus'
}
if test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=400):
    sys.exit(0)
sys.exit(1)
