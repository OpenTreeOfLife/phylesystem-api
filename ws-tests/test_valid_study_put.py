#!/usr/bin/env python
from opentreetesting import test_http_json_method, writable_api_host_and_oauth_or_exit
import datetime
import codecs
import json
import sys
import os

DOMAIN, auth_token = writable_api_host_and_oauth_or_exit(__file__)
study_id = "10"
SUBMIT_URI = DOMAIN + "/v3/study/" + study_id
data = {"output_nexml2json": "1.0.0"}
r = test_http_json_method(
    SUBMIT_URI, "GET", data=data, expected_status=200, return_bool_data=True
)
if not r[0]:
    sys.exit(0)
resp = r[1]
starting_commit_SHA = resp["sha"]
SUBMIT_URI = DOMAIN + "/v3/study/{s}".format(s=study_id)
n = resp["data"]
# refresh a timestamp so that the test generates a commit
m = n["nexml"]["^bogus_timestamp"] = datetime.datetime.utcnow().isoformat()
data = {
    "nexson": n,
    "auth_token": auth_token,
    "starting_commit_SHA": starting_commit_SHA,
}
r = test_http_json_method(
    SUBMIT_URI, "PUT", data=data, expected_status=200, return_bool_data=True
)
if not r[0]:
    sys.exit(0)
# print((r[1]))
