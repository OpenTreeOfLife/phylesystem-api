#!/usr/bin/env python
import sys
SCRIPT_NAME = __name__  #@TODO replace with logger...
ERR_STREAM = sys.stderr #@TODO replace with logger...
from nexson_validator import NexSON, NexSONError, ValidationLogger, FilteringLogger, WarningCodes, VERSION
def error(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: ERROR: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def warn(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: WARNING: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

def info(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

if __name__ == '__main__':
    import json
    import os
    import codecs
    import argparse
    import platform
    import datetime
    import uuid
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)

    parser = argparse.ArgumentParser(description='Validate a json file as Open Tree of Life NexSON')
    parser.add_argument('--verbose', dest='verbose', action='store_true', default=False, help='verbose output')
    parser.add_argument('--validate', dest='validate', action='store_true', default=False, help='warnings and error messages in JSON')
    parser.add_argument('--embed', dest='embed', action='store_true', default=False, help='embed the warnings and error messages in the NexSON meta element')
    parser.add_argument('--retain-deprecated', dest='retain_deprecated', action='store_true', default=False, help='do not update any deprecated syntax')
    parser.add_argument('--meta', dest='meta', action='store_true', default=False, help='warn about unvalidated meta elements')
    parser.add_argument('input', metavar='filepath', type=unicode, nargs=1, help='filename')
    args = parser.parse_args()
    SCRIPT_NAME = os.path.split(sys.argv[0])[-1]
    try:
        inp_filepath = args.input[0]
    except:
        sys.exit('Expecting a filepath to a NexSON file as the only argument.\n')
    inp = codecs.open(inp_filepath, 'rU', encoding='utf-8')
    try:
        obj = json.load(inp)
    except ValueError as vx:
        error('Not valid JSON.')
        if args.verbose:
            raise vx
        else:
            sys.exit(1)
    check_codes = list(WarningCodes.numeric_codes_registered)
    if not args.meta:
        v = FilteringLogger(codes_to_skip=[WarningCodes.UNVALIDATED_ANNOTATION], store_messages=True)
        check_codes.remove(WarningCodes.UNVALIDATED_ANNOTATION)
    else:
        v = ValidationLogger(store_messages=True)
    checks_performend = [WarningCodes.facets[i] for i in check_codes]
    if args.retain_deprecated:
        v.retain_deprecated = True
    try:
        n = NexSON(obj, v)
    except NexSONError as nx:
        error(nx.value)
        sys.exit(1)

    output = sys.stdout
    if args.validate:
        invoc = list(sys.argv[1:])
        invoc.remove(inp_filepath)
        uuid = "meta-" + str(uuid.uuid1())
        script_name = os.path.basename(sys.argv[0])
        annotation_label = "Open Tree NexSON validation"
        annotation = {
            "@property": "ot:annotation",
            "$": annotation_label,
            "@xsi:type": "nex:ResourceMeta",
            "author": {
                "name": script_name, 
                "url": "https://github.com/OpenTreeOfLife/api.opentreeoflife.org", 
                "description": "validator of NexSON constraints as well as constraints that would allow a study to be imported into the Open Tree of Life's phylogenetic synthesis tools",
                "version": VERSION,
                "invocation": {
                    "commandLine": invoc,
                    "checksPerformed": checks_performend,
                    'pythonVersion' : platform.python_version(),
                    'pythonImplementation' : platform.python_implementation(),
                }
            },
            "dateCreated": datetime.datetime.utcnow().isoformat(),
            "id": uuid,
            "messages": [],
            "isValid": (len(v.errors) == 0) and (len(v.warnings) == 0),
        }
        message_list = annotation["messages"]
        for m in v.errors:
            d = m.as_dict()
            d['severity'] = "ERROR"
            d['preserve'] = False
            message_list.append(d)
        for m in v.warnings:
            d = m.as_dict()
            d['severity'] = "WARNING"
            d['preserve'] = False
            message_list.append(d)
        if args.embed:
            n = obj['nexml']
            former_meta = n.setdefault('meta', [])
            if not isinstance(former_meta, list):
                former_meta = [former_meta]
                n['meta'] = former_meta
            else:
                indices_to_pop = []
                for annotation_ind, el in enumerate(former_meta):
                    try:
                        if (el.get('$') == annotation_label) and (el.get('author',{}).get('name') == script_name):
                            m_list = el.get('messages', [])
                            to_retain = []
                            for m in m_list:
                                if m.get('preserve'):
                                    to_retain.append(m)
                            if len(to_retain) == 0:
                                indices_to_pop.append(annotation_ind)
                            elif len(to_retain) < len(m_list):
                                el['messages'] = to_retain
                                el['dateModified'] = datetime.datetime.utcnow().isoformat()
                    except:
                        # different annotation structures could yield IndexErrors or other exceptions.
                        # these are not the annotations that you are looking for
                        pass

                if len(indices_to_pop) > 0:
                    # walk backwards so pops won't change the meaning of stored indices
                    for annotation_ind in indices_to_pop[-1::-1]:
                        former_meta.pop(annotation_ind)
            former_meta.append(annotation)
            json.dump(obj, sys.stdout, sort_keys=True, indent=0)
        else:
            json.dump(annotation, sys.stdout, sort_keys=True, indent=0)
    else:
        json.dump(obj, sys.stdout, sort_keys=True, indent=0)
