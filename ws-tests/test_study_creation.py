#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import datetime
import codecs
import json
import sys
import os

DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/'
inpf = codecs.open('data/1003.json', 'rU', encoding='utf-8')
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
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
}
if test_http_json_method(SUBMIT_URI,
                         'POST',
                         data=data,
                         expected_status=200):
    sys.exit(0)
sys.exit(1)
