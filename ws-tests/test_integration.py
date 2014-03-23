#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import datetime
import codecs
import json
import sys
import os


study_id = '9'
DOMAIN = config('host', 'apihost')

#A full integration test, with GET, PUT, POST, MERGE and a merge conflict, 


#test get and save sha
data = {'output_nexml2json':'1.2'}
SUBMIT_URI = DOMAIN + '/v1/study/{s}'.format(s=study_id)
r = test_http_json_method(SUBMIT_URI, 'GET', data=data, expected_status=200, return_bool_data=True)

assert(r[0]==True)

get_sha = r[1]["sha"]
n=r[1]["data"]
assert(get_sha)
#assert(get_sha=="5c845c47fc8a0b7b37b02bde9f0f59a399a3c434")

#PUT edits to a study
starting_commit_SHA = get_sha
SUBMIT_URI = DOMAIN + '/v1/study/{s}'.format(s=study_id)
fn = '/home/ejmctavish/projects/otapi/peyotl/peyotl/test/data/mini_par/mini_phyl/study/{s}/{s}.json'.format(s=study_id)
inpf = codecs.open(fn, 'rU', encoding='utf-8')
# refresh a timestamp so that the test generates a commit
n['nexml'][u'bogus_timestamp']=unicode(datetime.datetime.utcnow().isoformat())

data = { 'nexson' : n,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
r2 = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)

assert(r2[0]==True)
assert(r2[1]['resource_id']==study_id)
assert(r2[1]['merge_needed']==False)

#print(r2[1].keys())

'''

resource_id
starting_commit_SHA
SUBMIT_URI = DOMAIN + '/merge/v1/{}/{}'.format(resource_id,starting_commit_SHA)

data = {
         'auth_token': 'bogus'
}
if test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=400):
    sys.exit(0)
sys.exit(1)

'''