#!/usr/bin/env python
import sys
SCRIPT_NAME = __name__  #@TODO replace with logger...
ERR_STREAM = sys.stderr #@TODO replace with logger...
from nexson_validator import WarningCodes, create_validation_nexson, prepare_annotation, add_or_replace_annotation

def error(msg):
    global SCRIPT_NAME, ERR_STREAM
    ERR_STREAM.write('{n}: ERROR: {m}'.format(n=SCRIPT_NAME,
                                                m=msg))
    if not msg.endswith('\n'):
        ERR_STREAM.write('\n')

if __name__ == '__main__':
    import json
    import os
    import codecs
    import argparse
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
    if args.validate:
        codes_to_skip = []
        if not args.meta:
            codes_to_skip.append(WarningCodes.UNVALIDATED_ANNOTATION)
        output = sys.stdout
        invoc = list(sys.argv[1:])
        invoc.remove(inp_filepath)
        script_name = os.path.basename(sys.argv[0])
        
        validation_log, nexson_obj = create_validation_nexson(obj, codes_to_skip, retain_deprecated=bool(args.retain_deprecated))
        annotation = prepare_annotation(validation_log,
                                        author_name=script_name,
                                        invocation=invoc,
                                        annotation_label="Open Tree NexSON validation")
        if args.embed:
            add_or_replace_annotation(obj, annotation)
            json.dump(obj, sys.stdout, sort_keys=True, indent=0)
        else:
            json.dump(annotation, sys.stdout, sort_keys=True, indent=0)
    else:
        json.dump(obj, sys.stdout, sort_keys=True, indent=0)
