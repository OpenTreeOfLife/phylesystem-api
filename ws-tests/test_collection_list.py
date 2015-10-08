#!/usr/bin/env python
import sys, os
from opentreetesting import test_http_json_method, config
DOMAIN = config('host', 'apihost')
SUBMIT_URI = DOMAIN + '/v2/collections/find_collections'
#sys.stderr.write('Calling "{}"...\n'.format(SUBMIT_URI))
r = test_http_json_method(SUBMIT_URI,
                          'GET',
                          expected_status=200,
                          return_bool_data=True)
if not r[0]:
    sys.exit(1)
#print r[1]
