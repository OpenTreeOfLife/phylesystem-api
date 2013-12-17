#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import datetime
import codecs
import json
import sys
import os

# this makes it easier to test concurrent pushes to different branches
if len(sys.argv) > 1:
    study_id = sys.argv[1]
else:
    study_id = 1003

DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/%s' % study_id
inpf = codecs.open('../nexson-validator/tests/single/input/1003.json', 'rU', encoding='utf-8')
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
