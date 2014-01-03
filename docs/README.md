# Open Tree API Documentation

This file documents the design of the Open Tree API, including requirements defined by
the [Open Tree of Life](http://opentreeoflife.org) community and software team
and the reasons for various "details of implementation".

_Note that methods are also being documented in a wiki page in the main 'opentree' project._
https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs

_TODO: Consolidate these pages?_


## OToL API Version 1 Methods

NOTE: The dev.opentreeoflife.org hostname is a development URL and subject to change.

### Getting a Github Oauth token

Any API methods that allow writing (or changing the state of
the repo) require an authentication token. The examples below
assume a Github Oauth token is stored in the environment
variable

    $GITHUB_OAUTH_TOKEN

To get a Github OAuth token, you can use ```curl``` as well:

    curl -u USERNAME -X POST https://api.github.com/authorizations \
        --data '{"scopes":["public_repo"],"note":"description"}'

where USERNAME is your Github login/username. The above will
return JSON containing a "token" key, which is your new OAuth
token.

To put it into an environment variable:

    export GITHUB_OAUTH_TOKEN=codecafe

### Fetch a study

To get the entire NexSON of study N :

    curl http://dev.opentreeoflife.org/api/v1/study/N.json

### Updating a study

If you want to update study 10 with a file called
10-modified.json, the following command will accomplish that:

    curl -X PUT http://localhost:8080/api/default/v1/study/10.json?auth_token=$GITHUB_OAUTH_TOKEN \
    --data-urlencode nexson@10-modified.json

The above will create a commit with the updated JSON on a branch of the form

    USERNAME_study_ID

where USERNAME is the authenticated users Github login and ID
is the study ID number.

On success, it will return a JSON response similar to this:

    {
     "branch_name": "leto_study_13",
     "sha": "e13343535837229ced29d44bdafad2465e1d13d8",
     "description": "Updated study #13",
     "error": 0
     }

```branch_name``` is the WIP branch that was created, ```sha```
is the latest commit on that branch, ```description``` is a
textual description of what happened and ```error``` is set to
0.

On failure, ```error``` will be set to 1 and ```description``` will provide details on why the request failed.

[Here](https://github.com/OpenTreeOfLife/treenexus/compare/leto_study_9?expand=1)
is an example commit created by the OpenTree API.

### Creating a new study

To create a new study from a file in the current directory called ```study.json```:

    curl -X POST "http://localhost:8000/api/default/v1/study/?auth_token=$GITHUB_OAUTH_TOKEN" --data-urlencode nexson@study.json

### Syncing a WIP branch with Github

    curl -X POST http://dev.opentreeoflife.org/api/pull/v1/master?auth_token=$GITHUB_OAUTH_TOKEN



### Merge a study in a WIP branch

To merge branch X into branch Y:

    curl -X POST http://dev.opentreeoflife.org/api/merge/v1/X/Y?auth_token=$GITHUB_OAUTH_TOKEN

The default value for Y is the "master" branch, which is what most merges will want to do.

The following two commands are equivalent.

    curl -X POST http://dev.opentreeoflife.org/api/merge/v1/leto_study_1003?auth_token=$GITHUB_OAUTH_TOKEN

    curl -X POST http://dev.opentreeoflife.org/api/merge/v1/leto_study_1003/master?auth_token=$GITHUB_OAUTH_TOKEN

### Using different author information

By default, the API uses the name and email associated with the Github Oauth token to assign provenance to API calls. To over-ride that you can provide ```author_name``` and ```author_email``` arguments:

    curl -X PUT 'http://localhost:8000/api/default/v1/study/13.json?auth_token=$GITHUB_OAUTH_TOKEN&author_name=joe&author_email=joe@joe.com' --data-urlencode nexson@1003.json



All API calls are specific to the API version, which is a part
of the URL. This allows for new versions of the API to come out
which are not backward-compatible, while allowing old clients
to continue working with older API versions.

Any POST request attempting to update a study with invalid JSON
will be denied and an HTTP error code 400 will be returned.


## Authors

Jonathan "Duke" Leto

Jim Allman
