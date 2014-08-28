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

  * `repo_parent` should be a file path which holds 1 or more phyleystem-# repositories
with the data.

  * `git_ssh` and `pkey`


### Logging configuration

The behavior of the log for functions run from with a request is determined by the config
file. Specifically, the 

    [logging]
    level = debug
    filepath = /tmp/my-api.log
    formatter = rich

section of that file.

If you are developer of the phylesystem-api, and you want to see logging for functions
that are not called in the context of a request, you can use the environmental variables:

  * `OT_API_LOG_FILE_PATH` filepath of log file (StreamHandler if omitted)
  * `OT_API_LOGGING_LEVEL` (NotSet, debug, info, warning, error, or critical)
  * `OT_API_LOGGING_FORMAT` "rich", "simple" or "None" (None is default)

# Deploying

This git repository is meant to be a "web2py application", so you need to
create a symlink in ```$WEB2PY_ROOT/applications``` to the API repo directory:

   cd $WEB2PY_ROOT/application
   # this will make the app available under /api
   ln -sf /dir/with/api.opentreeoflife.org api

# Using the API from the command-line

See [docs/](https://github.com/OpenTreeOfLife/api.opentreeoflife.org/blob/master/docs/) for examples of how to use the API with ```curl```.

# Using the API from Python

See [peyotl](https://github.com/OpenTreeOfLife/peyotl) has wrappers for accessing phylesystem web services.
See the [peyotl wiki](https://github.com/OpenTreeOfLife/peyotl/wiki) for details.

# Authors

See the CREDITS file
