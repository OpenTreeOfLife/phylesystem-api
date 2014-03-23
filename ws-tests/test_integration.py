#!/usr/bin/env python
from opentreetesting import test_http_json_method, config
import datetime
import codecs
import copy
import json
import sys
import os



study_id = '9'
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v1/study/{s}'.format(s=study_id)

#A full integration test, with GET, PUT, POST, MERGE and a merge conflict, 
#test get and save sha
data = {'output_nexml2json':'1.2'}
r = test_http_json_method(SUBMIT_URI, 'GET', data=data, expected_status=200, return_bool_data=True)

assert(r[0]==True)

start_sha = r[1]["sha"]
blob=r[1]["data"]
assert(start_sha)

acurr_obj = blob
zcurr_obj = copy.deepcopy(blob)

# PUT edits to a study that should merge to master
starting_commit_SHA = start_sha
ac = acurr_obj['nexml'].get("^acount", 0)
ac += 1
acurr_obj['nexml']["^acount"] = ac

data = { 'nexson' : acurr_obj,
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
r2_sha=r2[1]['sha']

#test merge failure when new branch is behind master
# update Zcount so that file differs from previous commit
zc = zcurr_obj['nexml'].get("^zcount", 0)
zc += 1
zcurr_obj['nexml']["^zcount"] = zc
data = { 'nexson' : zcurr_obj,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}

r3 = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)

assert(r3[0]==True)
assert(r3[1]['resource_id']==study_id)
assert(r3[1]['merge_needed']==True)
r3_sha=r3[1]['sha']


# fetching studies (GETs in the API) should report 
# the existence of multiple branches for this study...
data = {'output_nexml2json':'1.2'}

rg1 = test_http_json_method(SUBMIT_URI, 'GET', data=data, expected_status=200, return_bool_data=True)
assert(rg1[0]==True)
assert(len(rg1[1]['branch2sha'])>=2)
#assert(rg1[1]['data']==acurr_obj) #@EJM isn't this what the data should be?

# but not for other studies...
alt_study_id='10'
data = {'output_nexml2json':'1.2'}
alt_SUBMIT_URI = DOMAIN + '/v1/study/{s}'.format(s=alt_study_id)
rg2 = test_http_json_method(alt_SUBMIT_URI, 'GET', data=data, expected_status=200, return_bool_data=True)
assert(rg2[0]==True)
assert(len(rg2[1]['branch2sha'])==1)
assert(rg2[1]['data']!=acurr_obj)


# add a fourth commit onto commit 2. This should merge to master
starting_commit_SHA = r2_sha
ac += 1
acurr_obj['nexml']["^acount"] = ac

data = { 'nexson' : acurr_obj,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
r4 = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)

assert(r4[0]==True)
assert(r4[1]['resource_id']==study_id)
assert(r4[1]['merge_needed']==False)


# add a fifth commit onto commit 3. This should still NOT merge to master
starting_commit_SHA = r3_sha
zc = zcurr_obj['nexml'].get("^zcount", 0)
zc += 1
zcurr_obj['nexml']["^zcount"] = zc
data = { 'nexson' : zcurr_obj,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}

r5 = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)

assert(r5[0]==True)
assert(r5[1]['resource_id']==study_id)
assert(r5[1]['merge_needed']==True)
r5_sha=r5[1]['sha']

# sixth commit is the merge
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/merge/v1/{s}'.format(s=study_id)

data = {
        'starting_commit_SHA' : r5_sha,
        'auth_token' :  os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
       
}

print('curl -X PUT http://localhost:8000/api/merge/v1/9/{}?auth_token=$GITHUB_OAUTH_TOKEN'.format(r5_sha))

#This part is not working...
'''
r6 = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=400,
                         return_bool_data=True)

print(r6[1].keys())

merged_sha = r6[1]['merged_sha']

        
        
# add a 7th commit onto commit 6. This should NOT merge to master because we don't give it the secret arg.
starting_commit_SHA = ?
zc += 1
zcurr_obj['nexml']["^zcount"] = zc

data = { 'nexson' : zcurr_obj,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
}
r7 = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)

assert(r7[0]==True)
assert(r7[1]['resource_id']==study_id)
assert(r7[1]['merge_needed']==True)


        
# add a 7th commit onto commit 6. This should merge to master because we don't give it the secret arg.
zc += 1
zcurr_obj['nexml']["^zcount"] = zc

data = { 'nexson' : zcurr_obj,
         'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
         'starting_commit_SHA': starting_commit_SHA,
         'merged_sha' : merged_sha
}
r7a = test_http_json_method(SUBMIT_URI,
                         'PUT',
                         data=data,
                         expected_status=200,
                         return_bool_data=True)

assert(r7a[0]==True)
assert(r7a[1]['resource_id']==study_id)
assert(r7a[1]['merge_needed']==False)
        

# after the merge we should be back down to 1 branch for this study
data = {'output_nexml2json':'1.2'}

rg3 = test_http_json_method(SUBMIT_URI, 'GET', data=data, expected_status=200, return_bool_data=True)
assert(rg1[0]==True)
assert(len(rg1[1]['branch2sha'])==1)
#print(r2[1].keys())


'''