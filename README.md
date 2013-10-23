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

# Authors

See the CREDITS file
