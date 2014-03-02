#!/usr/bin/env python
from ConfigParser import SafeConfigParser
from cStringIO import StringIO
import requests
import gzip
import json
import sys
import os

_CONFIG = None
_CONFIG_FN = None
if 'VERBOSE_TESTING' in os.environ:
    try:
        _VERBOSITY_LEVEL = int(os.environ['VERBOSE_TESTING'])
    except:
        _VERBOSITY_LEVEL = 1
else:
    _VERBOSITY_LEVEL = 0
def debug(s):
    if _VERBOSITY_LEVEL > 0:
        sys.stderr.write('testing-harness: {s}\n'.format(s=s))

def config(section=None, param=None):
    '''
    Returns the config object if `section` and `param` are None, or the 
        value for the requested parameter.
    
    If the parameter (or the section) is missing, the exception is logged and
        None is returned.
    '''
    global _CONFIG, _CONFIG_FN
    if _CONFIG is None:
        _CONFIG_FN = os.path.abspath('test.conf')
        _CONFIG = SafeConfigParser()
        _CONFIG.read(_CONFIG_FN)
    if section is None and param is None:
        return _CONFIG
    try:
        v = _CONFIG.get(section, param)
        return v
    except:
        sys.stderr.write('Config file "%s" does not contain option "%s in section "%s"\n' % (_CONFIG_FN, param, section))
        return None

def summarize_json_response(resp):
    sys.stderr.write('Sent request to %s\n' %(resp.url))
    raise_for_status(resp)
    try:
        results = resp.json()
    except:
        print 'Non json resp is:', resp.text
        return False
    if isinstance(results, unicode) or isinstance(results, str):
        print results
        er = json.loads(results)
        print er
        print json.dumps(er, sort_keys=True, indent=4)
        sys.stderr.write('Getting JavaScript string. Object expected.\n')
        return False
    print json.dumps(results, sort_keys=True, indent=4)
    return True

def summarize_gzipped_json_response(resp):
    sys.stderr.write('Sent request to %s\n' %(resp.url))
    raise_for_status(resp)
    try:
        uncompressed = gzip.GzipFile(mode='rb', fileobj=StringIO(resp.content)).read()
        results = uncompressed
    except:
        raise 
    if isinstance(results, unicode) or isinstance(results, str):
        er = json.loads(results)
        print json.dumps(er, sort_keys=True, indent=4)
        return True
    else:
        print 'Non gzipped response, but not a string is:', results
        return False

def get_obj_from_http(url,
                     verb='GET',
                     data=None,
                     headers=None):
    '''Call `url` with the http method of `verb`. 
    If specified `data` is passed using json.dumps
    returns the json content of the web service or raise an HTTP error
    '''
    if headers is None:
        headers = {
            'content-type' : 'application/json',
            'accept' : 'application/json',
        }
    if data:
        resp = requests.request(verb,
                                url,
                                headers=headers,
                                data=json.dumps(data),
                                allow_redirects=True)
    else:
        resp = requests.request(verb,
                                url,
                                headers=headers,
                                allow_redirects=True)
    debug('Sent {v} to {s}\n'.format(v=verb, s=resp.url))
    debug('Got status code {c}\n'.format(c=resp.status_code))
    if resp.status_code != 200:
        debug('Full response: {r}\n'.format(r=resp.text))
        raise_for_status(resp)
    return resp.json()

def test_http_json_method(url,
                     verb='GET',
                     data=None,
                     headers=None,
                     expected_status=200,
                     expected_response=None, 
                     return_bool_data=False):
    '''Call `url` with the http method of `verb`. 
    If specified `data` is passed using json.dumps
    returns True if the response:
         has the expected status code, AND
         has the expected content (if expected_response is not None)
    '''
    fail_return = (False, None) if return_bool_data else False
    if headers is None:
        headers = {
            'content-type' : 'application/json',
            'accept' : 'application/json',
        }
    if data:
        resp = requests.request(verb,
                                url,
                                headers=headers,
                                data=json.dumps(data),
                                allow_redirects=True)
    else:
        resp = requests.request(verb,
                                url,
                                headers=headers,
                                allow_redirects=True)
    debug('Sent {v} to {s}\n'.format(v=verb, s=resp.url))
    debug('Got status code {c} (expecting {e})\n'.format(c=resp.status_code,e=expected_status))
    if resp.status_code != expected_status:
        debug('Full response: {r}\n'.format(r=resp.text))
        raise_for_status(resp)
        # this is required for the case when we expect a 4xx/5xx but a successful return code is returned
        return fail_return
    if expected_response is not None:
        try:
            results = resp.json()
            if results != expected_response:
                debug('Did not get expect response content. Got:\n{s}'.format(s=resp.text))
                return fail_return
        except:
            debug('Non json resp is:' + resp.text)
            return fail_return
        if _VERBOSITY_LEVEL > 1:
            debug(unicode(results))
    elif _VERBOSITY_LEVEL > 1:
        debug('Full response: {r}\n'.format(r=resp.text))

    return (True, resp.json(), True) if return_bool_data else True

def raise_for_status(resp):
    try:
        resp.raise_for_status()
    except Exception, e:
        try:
            j = resp.json()
            m = '\n    '.join(['"{k}": {v}'.format(k=k, v=v) for k, v in r.items()])
            sys.stderr.write('resp.json = {t}'.format(t=m))
        except:
            if resp.text:
                sys.stderr.write('resp.text = {t}\n'.format(t=resp.text))
        raise e

