# The Open Tree Of Life API

[![Build Status](https://secure.travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org.png)](http://travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org)

This repository holds the code that runs The Open Tree Of Life API, which talks
to the backend datastore [phylesystem](https://github.com/OpenTreeOfLife/phylesystem).

# Introduction

See the [Version Control Strategy](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/blob/master/docs/vcs_strategy.md) for more details about design decisions and how to use submodules.

# Installation

There are a dependencies installable from pypi using pip, and the open
tree of life client-side python library is also used on the server side
for handling some aspects of NexSON.

    $ pip install -r requirements.txt
    $ cd ..

The first time you run, you'll need to:

    $ git clone https://github.com/OpenTreeOfLife/peyotl.git
    $ cd peyotl
    $ pip install -r requirements.txt
    $ python setup.py develop

subsequently changing to the <code>peyotl</code> directory and running

    $ git pull origin master

should be sufficient to get the latest changes.

# Configuration

    $ cp private/config.exampl private/config

then open private/config in a text editor and tweak it. 

**NEW in the translatingnexson branch**: a new config variable 'repo_nexml2json' was added.

# Deploying

This git repository is meant to be a "web2py application", so you need to
create a symlink in ```$WEB2PY_ROOT/applications``` to the API repo directory:

   cd $WEB2PY_ROOT/application
   # this will make the app available under /api
   ln -sf /dir/with/api.opentreeoflife.org api

# Using the API from the command-line

See [docs/](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/blob/master/docs/) for examples of how to use the API with ```curl```.

# Dealing with large studies

NOTE: This is a proposal and not yet implemented. All studies
are currently under 50MB and have a structure of:

    studies/N/N.json

On the backend, the API will ask phylesystem for the directory
containing study ```N```.  If the JSON representing that study
is greater than 50MB, it will be broken into multiple files to
be stored in Git, so they  will be merged together before a
response is sent. This is all transparent to the user of the
OToL API. Only people using the phylesystem data files directly
will need to handle this.

These files will have the structure of:

    studies/N/N-0.json
    studies/N/N-1.json
    ....
    studies/N/N-10.json


# Using the API from Python

See
[opentree_client.py](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/blob/master/sample_client/opentree_client.py)
for examples of using the API from Python.

# Authors

See the CREDITS file
