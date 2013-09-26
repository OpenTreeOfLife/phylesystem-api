# The Open Tree Of Life API

[![Build Status](https://secure.travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org.png)](http://travis-ci.org/OpenTreeOfLife/api.opentreeoflife.org.png)

This repository will hold the code that runs api.opentreeoflife.org, which talks
to the backend datastore [treenexus](https://github.com/OpenTreeOfLife/treenexus).

# Introduction

This repo currently has a single Git submodule at ``` ./treenexus ```

The first time you clone this repo, run this command to get the treenexus data:

     git submodule update --init --recursive

The ```--recursive``` option is currently optional.

# Authors

Jonathan "Duke" Leto
