#!/usr/bin/env python
import sys, os, json
from opentreetesting import config, get_obj_from_http
DOMAIN = config('host', 'apihost')
for study_id in sys.argv[1:]:
    SUBMIT_URI = DOMAIN + '/phylesystem/v1/study/' + study_id
    data = {'output_nexml2json':'1.2'}
    x = get_obj_from_http(SUBMIT_URI, 
                          'GET',
                          data=data)
    json.dump(x, sys.stdout, indent=0, sort_keys=True)
    sys.stdout.write('\n')
