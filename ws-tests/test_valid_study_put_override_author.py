#!/usr/bin/env python
from opentreetesting import test_http_json_method, config, exit_if_api_is_readonly
import datetime
import codecs
import json
import sys
import os

DOMAIN = config('host', 'apihost')
starting_commit_SHA = config('host', 'parentsha')

study_id="12"
SUBMIT_URI = DOMAIN + '/v1/study/{s}'.format(s=study_id)
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

exit_if_api_is_readonly(__file__)

data = { 'nexson' : n,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'author_name': "Some Author",
         'author_email': "author@author.com",
         'starting_commit_SHA': starting_commit_SHA,
}
if test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200):
    sys.exit(0)
sys.exit(1)
