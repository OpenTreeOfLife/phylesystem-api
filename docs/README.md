# OTOL API Design Document

This file documents the design of the OTOL API, including requirements defined by
the [Open Tree of Life](http://opentreeoflife.org) community and software team
and the reasons for various "details of implementation".

_Note that methods are also being documented in a wiki page in the main 'opentree' project._
https://github.com/OpenTreeOfLife/opentree/wiki/Open-Tree-of-Life-APIs

_TODO: Consolidate these pages?_


### OToL API Version 1 Methods

To get the entire NexSON of study N :

    curl http://dev.opentreeoflife.org/api/v1/study/N.json

NOTE: The above URL is a development URL and subject to change.

On the backend, the API will ask treenexus for the directory containing study
```N```.  If the JSON representing that study is greater than 50MB, it will be
broken into multiple files to be stored in Git, so they  will be merged
together before a response is sent. This is all transparent to the user of the
OToL API. Only people using the treenexus data files directly will need to
handle this.

These files will have the structure of:

    studies/N/N-0.json
    studies/N/N-1.json
    ....
    studies/N/N-10.json

To update/overwrite the entire NexSON for study N with a local file called
```N.json``` and an API key called "deadbeef":

    curl -X POST http://api.opentreeoflife.org/1/study/N.json?key=deadbeef \
        -H "Content-Type: Application/json" -d@N.json

TODO: Add mandatory author email address to associate to each POST which changes data.

All API calls are specific to the API version, which is a part of the URL. This
allows for new versions of the API to come out which are not
backward-compatible, while allowing old clients to continue working with older
API versions.

Any POST request attempting to update a study with invalid JSON will be denied
and an HTTP error code 400 will be returned.


## Authors

Jonathan "Duke" Leto

Jim Allman
