#!/usr/bin/env python
from celery import Celery
import requests
import traceback
import json
celery = Celery()
celery.config_from_object('celeryconfig')

@celery.task
def call_http_json(url,
              verb='GET',
              data=None,
              headers=None):
    if headers is None:
        headers = {
            'content-type' : 'application/json',
            'accept' : 'application/json',
        }
    with open('/tmp/celeryerr', 'a') as fe:
        fe.write("{} to \"{}\"\n".format(verb, url))
                
    resp = None
    try:
        if data:
            pass
            # resp = requests.request(verb,
            #                         url,
            #                         headers=headers,
            #                         data=json.dumps(data),
            #                         allow_redirects=True)
        else:
            resp = requests.request(verb, url, headers=headers, allow_redirects=True)
        resp.raise_for_status()
        return resp.status_code, resp.json()
    except:
        with open('/tmp/celeryerr', 'a') as fe:
            fe.write('E1: \n')
        try:
            x = resp.status_code
        except:
            with open('/tmp/celeryerr', 'a') as fe:
                fe.write('E2:\n')
            x = -1
        try:
            return x, 'Error response with JSON = ' + json.dumps(resp.json())
        except:
            with open('/tmp/celeryerr', 'a') as fe:
               fe.write('E3:\n')
            try:
                return x, 'Error: response with text = ' + resp.text
            except:
                m = 'Unknown error: ' + traceback.format_exc()
                with open('/tmp/celeryerr', 'a') as fe:
                    fe.write(m + '\n')
                return x, m


