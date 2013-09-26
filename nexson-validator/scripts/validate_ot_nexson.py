#!/usr/bin/env python
import sys
SCRIPT_NAME = __name__  #@TODO replace with logger...
ERR_STREAM = sys.stderr #@TODO replace with logger...

def error(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: ERROR: {m}\n'.format(n=SCRIPT_NAME,
                                                m=msg))

if __name__ == '__main__':
    import json
    import os
    import codecs

    SCRIPT_NAME = os.path.split(sys.argv[0])[-1]
    try:
        inp_filepath = sys.argv[1]
    except:
        sys.exit('Expecting a filepath to a NexSON file as the only argument.\n')
    inp = codecs.open(inp_filepath, 'rU', encoding='utf-8')
    try:
        obj = json.load(inp)
    except ValueError as vx:
        error('Not valid JSON.')
        sys.exit(1)
    print obj