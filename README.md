# The Open Tree Of Life API

[![Build Status](https://secure.travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org.png)](http://travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org)

This repository holds the code that runs The Open Tree Of Life API, which talks
to the backend datastore [treenexus](https://github.com/OpenTreeOfLife/treenexus).

# Introduction

See the [Version Control Strategy](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/blob/master/docs/vcs_strategy.md) for more details about design decisions and how to use submodules.

# Deploying

This git repository is meant to be a "web2py application", so you need to
create a symlink in ```$WEB2PY_ROOT/applications``` to the API repo directory:

   cd $WEB2PY_ROOT/application
   # this will make the app available under /api
   ln -sf /dir/with/api.opentreeoflife.org api

# Using the API

If you want to update study 10 with a file called 10-modified.json, the
following command will accomplish that:

    curl -v -X POST http://localhost:8080/api/default/v1/study/10.json?auth_token=$GITHUB_OAUTH_TOKEN \
    --data-urlencode nexson@10-modified.json

Note that it assumes a Github Oauth token is stored in the environment variable

    $GITHUB_OAUTH_TOKEN

To get a Github OAuth token, you can use ```curl``` as well:

    curl -v -u USERNAME -X POST https://api.github.com/authorizations \
        --data '{"scopes":["public_repo"],"note":"description"}'

where USERNAME is your Github login/username. The above will return JSON
containing a "token" key, which is your new OAuth token.

The above will create a commit with the update JSON on a branch of the form

    USERNAME_study_ID

where USERNAME is the authenticated users Github login and ID is the study ID
number.

[Here](https://github.com/OpenTreeOfLife/treenexus/compare/leto_study_9?expand=1)
is an example commit created by the OpenTree API.

# Using the API from Python

See
[opentree_client.py](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/blob/master/sample_client/opentree_client.py)
for examples of using the API from Python.

# Authors

See the CREDITS file
