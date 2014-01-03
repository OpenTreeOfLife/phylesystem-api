#!/usr/bin/env python

import requests
import codecs
import json
import sys
import os

# Some of these examples require a Github OAUTH token stored in
# the environment variable GITHUB_OAUTH_TOKEN
# See
# https://github.com/OpenTreeOfLife/api.opentreeoflife.org#using-the-api
# for details about generating the token

if len(sys.argv) > 1:
    apihost = sys.argv[1]
else:
    apihost = "http://127.0.0.1:8000"

headers = {
    'content-type' : 'application/json',
    'accept' : 'application/json',
}

def example_get(study_id=9):
    "Read a study via GET"
    url  = "%s/api/default/%s%s" % (apihost, "v1/study/", study_id)
    print "Requesting GET %s" % url
    resp = requests.get(url, headers=headers, allow_redirects=True)
    print "Got status code: %s" % resp.status_code
    show_response(resp)

def example_put(study_id=9):
    "Update a study via PUT"

    url  = "%s/api/default/%s%s" % (apihost, "v1/study/", study_id)
    print "Requesting PUT %s" % url

    study_file = codecs.open("study.json", "rU", encoding="utf-8")
    nexson     = json.load(study_file)

    data = { 'nexson' : nexson,
            'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
    }

    resp = requests.put(url, data=json.dumps(data), headers=headers, allow_redirects=True)
    show_response(resp)

def example_post():
    "Create a study via POST"
    url  = "%s/api/default/%s" % (apihost, "v1/study/")
    print "Requesting POST %s" % url

    study_file = codecs.open("study.json", "rU", encoding="utf-8")
    nexson     = json.load(study_file)

    data = { 'nexson' : nexson,
            'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token'),
    }

    resp = requests.post(url, data=json.dumps(data), headers=headers, allow_redirects=True)
    show_response(resp)
    data = resp.json()
    return data["branch_name"]

def example_merge(branch):
    data = { 'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token') }

    url  = "%s/api/merge/v1/%s/%s" % (apihost, branch, "master")

    resp = requests.post(url, data=json.dumps(data), headers=headers, allow_redirects=True)

    show_response(resp)

def example_pull():
    "Example that syncs the local master branch with our remote master branch"
    data = { 'auth_token': os.environ.get('GITHUB_OAUTH_TOKEN', 'bogus_token') }

    url  = "%s/api/pull/v1/master" % ( apihost )

    resp = requests.post(url, data=json.dumps(data), headers=headers, allow_redirects=True)

    show_response(resp)

def show_response(resp):
    print "Got status code: %s" % resp.status_code

    try:
        json_response = resp.json()
        print json_response
    except:
        text = resp.text
        print text

# Update/sync a branch
example_pull()

# Read a study
example_get()

# Modify a study
example_put()

# Create a new study
branch = example_post()
print "Branch name is %s" % branch

example_merge(branch)
