# Version Control Strategy for OpenTree

This document describes the requirements and
justifications for the each architectural decision
that has been made regarding Version Control. It will
be a living document that changes as the community,
data and technology of OpenTree changes.

# Data repository

Currently the source data for OpenTree consists of a
collection of JSON files (which are in the NexSON
format) which live in the treenexus Github repo.

# Code repository

The code implementing the OpenTree API lives on [Github](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/) and includes the data repository as a Git submodule.

# WIP branches

When a change to NexSON data is submitted via the OpenTree API, it is made on
what we refer to as a "WIP branch", which has a name of the form
"USERNAME_study_N" where USERNAME is a github username and N is the study ID.

If the same user makes multiple edits to a single study, they will appear as
multiple commits on that WIP branch. If that user makes edits to another study
M, they will go onto the branch "USERNAME_study_M".

This allows multiple curators to work on the same study without stepping on
each others toes during the curation process. There is still the possibilty
that curators will make incompatible changes, which means the first one to
merge their WIP branch will merge cleanly, but when the second curator branch
is attempted to be merged, conflicts could arise if the curators edited the
same parts of the NexSON.

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
