# The Open Tree Of Life API

[![Build Status](https://secure.travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org.png)](http://travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org)

This repository holds the code that runs The Open Tree Of Life API, which talks
to the backend datastore [treenexus](https://github.com/OpenTreeOfLife/treenexus).

# Introduction

This repo currently has a single Git submodule at ``` ./treenexus ```

The first time you clone this repo, run this command to get the treenexus data:

     git submodule update --init --recursive

The ```--recursive``` option is currently optional.

# Why submodules?

Using treenexus as a submodule allows us to have various branches and tags in
our datastore and point different branches of this repo at specific commits in
the datastore.

## Updating the treenexus submodule

The following commands can be copy and pasted to update our
submodule to the latest commit on the master branch of treenexus.git

    cd treenexus

    # this will pull in new changes from the main treenexus.git
    # on the master branch
    git pull        # or git pull --rebase
    cd ..

    # this tells our repo to update the commit that our submodule
    # points to in treenexus
    git add treenexus
    git commit -m "Update treenexus submodule pointer"

To send these new changes to Github:

    git push

Let's say you are on a branch on this repo called ```feature_api```
and you want to our submodule to point to the latest commit in the
```feature_treenexus``` branch:

    git checkout feature_api
    cd treenexus

    git pull
    git checkout feature_treenexus
    cd ..

    # this tells our repo to update the commit that our submodule
    # points to in treenexus
    git add treenexus
    git commit -m "Update treenexus submodule pointer"

Similarly, you can checkout an arbitrary SHA1 and have our submodule
point to that by doing this:

    git checkout feature_api
    cd treenexus

    git pull
    git checkout SHA1 # this will create a "detached HEAD"
    cd ..

    # this tells our repo to update the commit that our submodule
    # points to in treenexus
    git add treenexus
    git commit -m "Update treenexus submodule pointer"

# Deploying

This git repository is meant to be a "web2py application", so you need to
create a symlink in ```$WEB2PY_ROOT/applications``` to the API repo directory:

   cd $WEB2PY_ROOT/application
   # this will make the app available under /api
   ln -sf /dir/with/api.opentreeoflife.org api

# Authors

See the CREDITS file
