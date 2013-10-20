#!/usr/bin/env python
import sys
import codecs
from cStringIO import StringIO

VERSION = '0.0.2a'


class NexSONError(Exception):
    def __init__(self, v):
        self.value = v
    def __str__(self):
        return repr(self.v)

# An enum of WARNING_CODES
class WarningCodes():
    facets = ['MISSING_MANDATORY_KEY',
              'MISSING_OPTIONAL_KEY',
              'UNRECOGNIZED_KEY',
              'MISSING_LIST_EXPECTED',
              'DUPLICATING_SINGLETON_KEY',
              'REFERENCED_ID_NOT_FOUND',
              'REPEATED_ID',
              'MULTIPLE_ROOT_NODES',
              'NO_ROOT_NODE',
              'MULTIPLE_EDGES_FOR_NODES',
              'CYCLE_DETECTED',
              'DISCONNECTED_GRAPH_DETECTED',
              'INCORRECT_ROOT_NODE_LABEL',
              'TIP_WITHOUT_OTU',
              'TIP_WITHOUT_OTT_ID',
              'MULTIPLE_TIPS_MAPPED_TO_OTT_ID',
              'NON_MONOPHYLETIC_TIPS_MAPPED_TO_OTT_ID',
              'INVALID_PROPERTY_VALUE',
              'PROPERTY_VALUE_NOT_USEFUL',
              'UNRECOGNIZED_PROPERTY_VALUE',
              'MULTIPLE_TREES',
              'UNVALIDATED_ANNOTATION',
              'UNRECOGNIZED_TAG',
              'CONFLICTING_PROPERTY_VALUES',
              'NO_TREES',
              ]
    numeric_codes_registered = []
for _n, _f in enumerate(WarningCodes.facets):
    setattr(WarningCodes, _f, _n)
    WarningCodes.numeric_codes_registered.append(_n)

def write_warning(out, prefix, wc, data, container, subelement):
    if wc == WarningCodes.MISSING_LIST_EXPECTED:
        out.write('{p}Expected a list found "{k}"'.format(p=prefix, k=type(data)))
    elif wc == WarningCodes.DUPLICATING_SINGLETON_KEY:
        out.write('{p}Multiple instances found for a key ("{k}") which was expected to be found once'.format(p=prefix, k=data))
    elif wc == WarningCodes.REPEATED_ID:
        out.write('{p}An ID ("{k}") was repeated'.format(p=prefix, k=data))
    elif wc == WarningCodes.REFERENCED_ID_NOT_FOUND:
        out.write('{p}An ID Reference did not match a previous ID ("{k}": "{v}")'.format(p=prefix, k=data['key'], v=data['value']))
    elif wc == WarningCodes.MULTIPLE_ROOT_NODES:
        out.write('{p}Multiple nodes in a tree were flagged as being the root node ("{k}" was not the first)'.format(p=prefix, k=data))
    elif wc == WarningCodes.NO_ROOT_NODE:
        out.write('{p}No node in a tree was flagged as being the root node'.format(p=prefix))
    elif wc == WarningCodes.TIP_WITHOUT_OTU:
        out.write('{p}Tip node without a valid @otu value'.format(p=prefix, n=data.nexson_id))
    elif wc == WarningCodes.PROPERTY_VALUE_NOT_USEFUL:
        k, v = data['key'], data['value']
        out.write('{p}Unhelpful or deprecated value "{v}" for property "{k}"'.format(p=prefix, k=k, v=v))
    elif wc == WarningCodes.CONFLICTING_PROPERTY_VALUES:
        s = u", ".join([u'"{k}"="{v}"'.format(k=i[0], v=i[1]) for i in data])
        out.write('{p}Conflicting values for properties: {s}'.format(p=prefix, s=s))
    elif wc == WarningCodes.UNRECOGNIZED_PROPERTY_VALUE:
        k, v = data['key'], data['value']
        out.write('{p}Unrecognized value "{v}" for property "{k}"'.format(p=prefix, k=k, v=v))
    elif wc == WarningCodes.INVALID_PROPERTY_VALUE:
        k, v = data['key'], data['value']
        out.write('{p}Invalid value "{v}" for property "{k}"'.format(p=prefix, k=k, v=v))
    elif wc == WarningCodes.UNVALIDATED_ANNOTATION:
        k, v = data['key'], data['value']
        m = u'{p}Annotation found, but not validated: "{k}" -> "{v}"'.format(p=prefix, k=k, v=v)
        out.write(m)
    elif wc == WarningCodes.MULTIPLE_TREES:
        out.write('{p}Multiple trees were found without an indication of which tree is preferred'.format(p=prefix))
    elif wc == WarningCodes.NO_TREES:
        out.write('{p}No trees were found, or all trees were flagged for deletion'.format(p=prefix))
    elif wc == WarningCodes.UNRECOGNIZED_TAG:
        out.write(u'{p}Unrecognized value for a tag: "{s}"'.format(p=prefix, s=data))
    elif wc == WarningCodes.MULTIPLE_TIPS_MAPPED_TO_OTT_ID:
        id_list = [i.nexson_id for i in data['node_list']]
        id_list.sort()
        s = ', '.join(['"{i}"'.format(i=i) for i in id_list])
        out.write('{p}Multiple nodes ({s}) are mapped to the OTT ID "{o}"'.format(p=prefix,
                                                                            s=s,
                                                                            o=data['ott_id'],
                                                                            ))
    elif wc == WarningCodes.NON_MONOPHYLETIC_TIPS_MAPPED_TO_OTT_ID:
        sl = [(i[0].nexson_id, i) for i in data['clades']]
        sl.sort()
        str_list = []
        for el in sl:
            str_list.append('"{s}"'.format(s='", "'.join([i.nexson_id for i in el[1]])))
        s = ' +++ '.join([i for i in str_list])
        out.write('{p}Multiple nodes that do not form the tips of a clade are mapped to the OTT ID "{o}". The clades are {s}'.format(p=prefix,
                                                                            s=s,
                                                                            o=data['ott_id'],
                                                                            ))
    elif wc == WarningCodes.TIP_WITHOUT_OTT_ID:
        out.write('{p}Tip node mapped to an OTU ("{o}") which does not have an OTT ID'.format(p=prefix, 
                                                        n=data.nexson_id,
                                                        o=data._otu.nexson_id))
    elif wc == WarningCodes.MULTIPLE_EDGES_FOR_NODES:
        nd = data['node']
        ed = data['edge']
        out.write('{p}A node ("{n}") has multiple edges to parents ("{f}" and "{s}")'.format(p=prefix,
                                                                                n=nd.nexson_id,
                                                                                f=nd._edge.nexson_id,
                                                                                s=ed.nexson_id))
    elif wc == WarningCodes.INCORRECT_ROOT_NODE_LABEL:
        nd = data['tagged']
        node_without_parent = data['node_without_parent']
        out.write('{p}The node flagged as the root ("{t}") is not the node without a parent ("{r}")'.format(p=prefix,
                                                                                t=nd.nexson_id,
                                                                                r=node_without_parent.nexson_id))
    elif wc == WarningCodes.CYCLE_DETECTED:
        out.write('{p}Cycle in a tree detected passing througn node "{n}"'.format(p=prefix, n=data.nexson_id))
    elif wc == WarningCodes.DISCONNECTED_GRAPH_DETECTED:
        out.write('{p}Disconnected graph found instead of tree including root nodes:'.format(p=prefix))
        for index, el in enumerate(data):
            if index ==0:
                out.write('"{i}"'.format(i=el.nexson_id))
            else:
                out.write(', "{i}"'.format(i=el.nexson_id))
    else:
        assert(False)
    if subelement:
        out.write(' in "{el}"'.format(el=subelement))
    if container is not None:
        out.write(' in "{el}"'.format(el=container.get_tag_context()))
    out.write('\n')

class SeverityCodes(object):
    ERROR, WARNING = range(2)
    facets = ['ERROR', 'WARNING']

class WarningMessage(object):
    def __init__(self,
                 warning_code,
                 data,
                 container,
                 subelement='',
                 source_identifier=None,
                 severity=SeverityCodes.WARNING,
                 prop_name=''):
        self.warning_code = warning_code
        self.warning_data = data
        self._container = container
        self.subelement = subelement
        self.source_identifier = source_identifier
        self.severity = severity
        if prop_name:
            self.prop_name = prop_name
        else:
            if warning_code == WarningCodes.REFERENCED_ID_NOT_FOUND:
                self.prop_name = data['key']
            elif warning_code == WarningCodes.UNRECOGNIZED_TAG:
                self.prop_name = 'ot:tag'
            else:
                self.prop_name = None
    def write(self, outstream, prefix):
        write_warning(outstream,
                      prefix,
                      self.warning_code,
                      self.warning_data,
                      self._container,
                      self.subelement)
    def __unicode__(self, prefix=''):
        b = StringIO()
        ci = codecs.lookup('utf8')
        s = codecs.StreamReaderWriter(b, ci.streamreader, ci.streamwriter)
        self.write(s, prefix)
        return s.getvalue()
    def getvalue(self, prefix=''):
        return self.__unicode__(prefix=prefix)
    def as_dict(self):
        return {
            'severity': SeverityCodes.facets[self.severity],
            'code': WarningCodes.facets[self.warning_code],
            'comment': self.__unicode__(),
            'data': self.convert_data_for_json(),
            'refersTo': self._container.get_path_dict(self.subelement, self.prop_name)
        }
    def convert_data_for_json(self):
        wc = self.warning_code
        data = self.warning_data
        if wc == WarningCodes.MISSING_LIST_EXPECTED:
            return type(data)
        elif wc in [WarningCodes.NO_ROOT_NODE,
                    WarningCodes.TIP_WITHOUT_OTU,
                    WarningCodes.MULTIPLE_TREES,
                    WarningCodes.NO_TREES,
                    WarningCodes.TIP_WITHOUT_OTT_ID,
                    WarningCodes.MULTIPLE_EDGES_FOR_NODES,
                    WarningCodes.INCORRECT_ROOT_NODE_LABEL,
                    WarningCodes.DISCONNECTED_GRAPH_DETECTED,
                    ]:
            return None
        elif wc == WarningCodes.MULTIPLE_TIPS_MAPPED_TO_OTT_ID:
            id_list = [i.nexson_id for i in data['node_list']]
            id_list.sort()
            return {'nodes': id_list}
        elif wc == WarningCodes.NON_MONOPHYLETIC_TIPS_MAPPED_TO_OTT_ID:
            sl = [(i[0].nexson_id, i) for i in data['clades']]
            sl.sort()
            str_list = []
            for el in sl:
                str_list.append([i.nexson_id for i in el[1]])
            return {'nodes': str_list}
        elif wc == WarningCodes.CYCLE_DETECTED:
            return data.nexson_id
        else:
            return data
    def _write_message_suffix(self, out):
        if self.subelement:
            out.write(' in "{el}"'.format(el=self.subelement))
        if self._container is not None:
            out.write(' in "{el}"'.format(el=self._container.get_tag_context()))
        out.write('\n')

class UnrecognizedKeyWarning(WarningMessage):
    def __init__(self, key, container, subelement='', source_identifier=None, severity=SeverityCodes.WARNING, prop_name=''):
        WarningMessage.__init__(self, WarningCodes.UNRECOGNIZED_KEY, data=key, container=container, subelement=subelement, source_identifier=source_identifier, severity=severity, prop_name=prop_name)
        self.key = key
    def write(self, outstream, prefix):
        outstream.write('{p}Unrecognized key "{k}"'.format(p=prefix, k=self.key))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.key

class MissingOptionalKeyWarning(WarningMessage):
    def __init__(self, key, container, subelement='', source_identifier=None, severity=SeverityCodes.WARNING, prop_name=''):
        WarningMessage.__init__(self, WarningCodes.MISSING_OPTIONAL_KEY, data=key, container=container, subelement=subelement, source_identifier=source_identifier, severity=severity, prop_name=prop_name)
        self.key = key
    def write(self, outstream, prefix):
        outstream.write('{p}Missing optional key "{k}"'.format(p=prefix, k=self.key))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.key

class MissingMandatoryKeyWarning(WarningMessage):
    def __init__(self, key, container, subelement='', source_identifier=None, severity=SeverityCodes.WARNING, prop_name=''):
        WarningMessage.__init__(self, WarningCodes.MISSING_MANDATORY_KEY, data=key, container=container, subelement=subelement, source_identifier=source_identifier, severity=severity, prop_name=prop_name)
        self.key = key
    def write(self, outstream, prefix):
        outstream.write('{p}Missing required key "{k}"'.format(p=prefix, k=self.key))
        self._write_message_suffix(outstream)
    def convert_data_for_json(self):
        return self.key

class DefaultRichLogger(object):
    def __init__(self, store_messages=False):
        self.out = sys.stderr
        self.source_identifier = None
        self.store_messages_as_obj = store_messages
        self.warnings = []
        self.errors = []
        self.prefix = ''
        self.retain_deprecated = False
    def warn(self, warning_code, data, container, subelement=''):
        m = WarningMessage(warning_code, data, container, subelement, self.source_identifier, severity=SeverityCodes.WARNING)
        self.warning(m)
    def warning(self, m):
        if self.store_messages_as_obj:
            self.warnings.append(m)
        else:
            m.write(self.out, self.prefix)
    def error(self, warning_code, data, container, subelement=''):
        m = WarningMessage(warning_code, data, container, subelement, self.source_identifier, severity=SeverityCodes.ERROR)
        self.emit_error(m)
    def emit_error(self, m):
        if self.store_messages_as_obj:
            self.errors.append(m)
        else:
            raise NexSONError(m.getvalue(self.prefix))

class ValidationLogger(DefaultRichLogger):
    def __init__(self, store_messages=False):
        DefaultRichLogger.__init__(self, store_messages=store_messages)
    def warning(self, m):
        if not self.store_messages_as_obj:
            m = m.getvalue(self.prefix)
        self.warnings.append(m)
    def emit_error(self, m):
        if not self.store_messages_as_obj:
            m = m.getvalue(self.prefix)
        self.errors.append(m)

class FilteringLogger(ValidationLogger):
    def __init__(self, codes_to_register=None, codes_to_skip=None, store_messages=False):
        ValidationLogger.__init__(self, store_messages=store_messages)
        self.codes_to_skip = set()
        if codes_to_register:
            self.registered = set(codes_to_register)
            if codes_to_skip:
                for el in codes_to_skip:
                    self.codes_to_skip.add(el)
                    assert el not in self.registered
        else:
            assert codes_to_skip
            self.registered = set(WarningCodes.numeric_codes_registered)
            for el in codes_to_skip:
                self.codes_to_skip.add(el)
                self.registered.remove(el)

    def warning(self, m):
        if m.warning_code in self.codes_to_skip:
            return
        if m.warning_code in self.registered:
            ValidationLogger.warning(self, m)
    def emit_error(self, m):
        if m.warning_code in self.codes_to_skip:
            return
        if m.warning_code in self.registered:
            ValidationLogger.emit_error(self, m)

def check_key_presence(d, schema, rich_logger):
    '''Issues errors if `d` does not contain keys in the schema.PERMISSIBLE_KEYS iterable,
    warnings if `d` lacks keys listed in schema.EXPECETED_KEYS, or if `d` contains
    keys not listed in schema.PERMISSIBLE_KEYS.
    schema.get_tag_context() is used to tag any warning/errors
    '''
    for k in d.keys():
        if k not in schema.PERMISSIBLE_KEYS:
            rich_logger.warning(UnrecognizedKeyWarning(k, container=schema))
    for k in schema.EXPECETED_KEYS:
        if k not in d:
            rich_logger.warning(MissingOptionalKeyWarning(k, container=schema))
    for k in schema.REQUIRED_KEYS:
        if k not in d:
            rich_logger.emit_error(MissingMandatoryKeyWarning(k, container=schema, severity=SeverityCodes.ERROR))
    

class NexsonDictWrapper(object):
    '''Base class adding the nexson_id property'''
    REQUIRED_KEYS = tuple()
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = tuple()
    TAG_CONTEXT = ''
    def __init__(self, o, rich_logger=None, container=None):
        self._raw = o
        self._container = container
        if rich_logger is None:
            self._logger = DefaultRichLogger()
        else:
            self._logger = rich_logger
    def get_path_dict(self, subelement, prop_name):
        assert False
    def get_nexson_id(self):
        return self._raw.get('@id')
    nexson_id = property(get_nexson_id)

    def get_tag_context(self):
        return '{f}(id={i})'.format(f=self.TAG_CONTEXT, i=self.nexson_id)

    def _consume_meta(self, o, rich_logger=None, expected_keys=None):
        '''Looks for a `meta` key to list in `o` (warns if not a list, but does not warn if absent)
        Converts each meta object to a Meta instance.
        adds 3 attributes to "self"
            _meta_list  - list of all Meta objects (in input order)
            _meta2value - dict mapping property_name  to value or property_name to MetaValueList of MetaValueList
            _meta2list  - dict mapping property_name to list of Meta items
             
        '''
        ml, mv, mld = _read_meta_list(o, self, self._logger)
        assert(not getattr(self, '_meta_list', None))
        assert(not getattr(self, '_meta2value', None))
        assert(not getattr(self, '_meta2list', None))
        self._meta_list = ml
        self._meta2value = mv
        self._meta2list = mld
        if (expected_keys is not None) and (rich_logger is not None):
            for k, v in mv.iteritems():
                if k not in expected_keys:
                    rich_logger.warn(WarningCodes.UNVALIDATED_ANNOTATION, {'key':k, 'value': v}, container=self, subelement='meta')
    def get_singelton_meta(self, property_name, default=None, warn_if_missing=True):
        v = self._meta2value.get(property_name)
        if v is None:
            if warn_if_missing:
                self._logger.warning(MissingOptionalKeyWarning('@property=' + property_name, container=self, subelement='meta'))
            v = default
        elif isinstance(v, MetaValueList):
            self._logger.error(WarningCodes.DUPLICATING_SINGLETON_KEY, '@property=' + property_name, container=self, subelement='meta')
        return v
    def replace_meta_property_name(self, old_name, new_name):
        meta_el_list = self._meta2list.get(old_name)
        if not bool(meta_el_list):
            return False
        for meta_el in meta_el_list:
            v = self._meta2value[old_name]
            if isinstance(v, MetaValueList):
                v.remove(meta_el.value)
            else:
                del self._meta2value[old_name]
            v = self._meta2list[old_name]
            v.remove(meta_el)
            if len(v) == 0:
                del self._meta2list[old_name]
            meta_el.property_name = new_name
            _add_meta_to_structs(meta_el, self._meta2value, self._meta2list)
            return True
    def get_list_meta(self, property_name, warn_if_missing=True):
        v = self._meta2value.get(property_name)
        if v is None:
            if warn_if_missing:
                self._logger.warning(MissingOptionalKeyWarning('@property=' + property_name, container=self, subelement='meta'))
            v = []
        return v
    def consume_meta_and_check_keys(self, d, rich_logger):
        '''calls check_key_presence and _consume_meta
        '''
        check_key_presence(d, self, rich_logger)
        self._consume_meta(d, rich_logger, self.EXPECTED_META_KEYS)

class MetaValueList(list):
    pass

class Meta(NexsonDictWrapper):
    REQUIRED_KEYS = ('$', '@property', '@xsi.type')
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = REQUIRED_KEYS
    def __init__(self, o, rich_logger, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
    def get_property_name(self):
        return self._raw.get('@property')
    def set_property_name(self, v):
        self._raw['@property'] = v
    property_name = property(get_property_name, set_property_name)
    def get_property_value(self):
        v = self._raw.get('@xsi:type')
        if v == 'nex:ResourceMeta':
            return self._raw.get('@href')
        return self._raw.get('$')
    value = property(get_property_value)

OTUMeta = Meta

def _add_meta_to_structs(meta_el, to_meta_value, to_meta_list):
    mk = meta_el.property_name
    v = meta_el.value
    cv = to_meta_value.setdefault(mk, v)
    if cv is not v:
        if not isinstance(cv, MetaValueList):
            to_meta_value[mk] = MetaValueList([cv, v])
        else:
            to_meta_value[mk].append(v)
    to_meta_list.setdefault(mk, []).append(meta_el)

def _read_meta_list(o, container, rich_logger):
    '''Looks for a `meta` key to list in `o` (warns if not a list, but does not warn if absent)
    Converts each meta object to a Meta instance.
    returns a tuple of 3 elements:
        list of all Meta objects (in input order)
        dict mapping property_name  to value or property_name to MetaValueList of MetaValueList
        dict mapping property_name to list of Meta items
         
    '''
    meta_list = []
    to_meta_value = {}
    to_meta_list = {}
    m = o.get('meta', [])
    if isinstance(m, dict):
        m = [m]
    if not isinstance(m, list):
        rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, m, container=container, subelement='meta')
    else:
        for el in m:
            meta_el = Meta(el, rich_logger, container=container)
            meta_list.append(meta_el)
            _add_meta_to_structs(meta_el, to_meta_value, to_meta_list)
    return (meta_list, to_meta_value, to_meta_list)

class OTU(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECETED_KEYS = ('@id',)
    PERMISSIBLE_KEYS = ('@id', '@about', '@label', 'meta')
    EXPECTED_META_KEYS = ('ot:ottid', 'ot:ottolid','ot:originalLabel')
    TAG_CONTEXT = 'otu'

    def __init__(self, o, rich_logger, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self.consume_meta_and_check_keys(o, rich_logger)
        self._ott_id = self.get_singelton_meta('ot:ottid', warn_if_missing=False)
        if self._ott_id is None:
            self._ott_id = self.get_singelton_meta('ot:ottolid', warn_if_missing=False)
            if self._ott_id is not None and (rich_logger is None or (not rich_logger.retain_deprecated)):
                self.replace_meta_property_name('ot:ottolid', 'ot:ottid')
        if self._ott_id is None:
            self.get_singelton_meta('ot:ottid') # trigger a warning
        self._original_label = self.get_singelton_meta('ot:originalLabel')
    def get_path_dict(self, subelement, prop_name):
        d = {
            'top': 'otus',
            'otusID': self._container.nexson_id,
            'otuID': self.nexson_id,
            'inMeta': False,
        }
        if subelement:
            assert subelement == 'meta'
            d['inMeta'] = True
        if prop_name:
            d['property'] = prop_name
        return d

class Edge(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id', '@source', '@target')
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = tuple(['@length'] + list(REQUIRED_KEYS))
    EXPECTED_META_KEYS = tuple()
    TAG_CONTEXT = 'edge'
    def __init__(self, o, rich_logger, nodes, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self.consume_meta_and_check_keys(o, rich_logger)
        self._source = None
        self._target = None
        sid = o.get('@source')
        if sid is not None:
            self._source = nodes.get(sid)
            if self._source is None:
                rich_logger.error(WarningCodes.REFERENCED_ID_NOT_FOUND,
                                  {'key': '@source',
                                   'value': sid},
                                  container=self)
            else:
                self._source._children.append(self)
        tid = o.get('@target')
        if tid is not None:
            self._target = nodes.get(tid)
            if self._target is None:
                rich_logger.error(WarningCodes.REFERENCED_ID_NOT_FOUND,
                                  {'key': '@target',
                                   'value': tid},
                                  container=self)
            elif self._target._edge is not None:
                rich_logger.error(WarningCodes.MULTIPLE_EDGES_FOR_NODES, 
                                  {'node': self._target,
                                  'edge': self
                                  }, 
                                  container=self)
            else:
                self._target._edge = self
    def get_path_dict(self, subelement, prop_name):
        d = {
            'top': 'trees',
            'treesID': self._container._container.nexson_id,
            'treeID': self._container.nexson_id,
            'edgeID': self.nexson_id,
            'inMeta': False,
        }
        if subelement:
            assert subelement == 'meta'
            d['inMeta'] = True
        if prop_name:
            d['property'] = prop_name
        return d


class Node(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = ('@id', '@otu', '@root')
    EXPECTED_META_KEYS = tuple()
    TAG_CONTEXT = 'node'
    def get_path_dict(self, subelement, prop_name):
        d = {
            'top': 'trees',
            'treesID': self._container._container.nexson_id,
            'treeID': self._container.nexson_id,
            'nodeID': self.nexson_id,
            'inMeta': False,
        }
        if subelement:
            assert subelement == 'meta'
            d['inMeta'] = True
        if prop_name:
            d['property'] = prop_name
        return d
    def __init__(self, o, rich_logger, otu_dict, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self.consume_meta_and_check_keys(o, rich_logger)
        self._is_root = o.get('@root', False)
        self._edge = None
        self._children = []
        self._otu = None
        v = o.get('@otu')
        if v is not None:
            self._otu = otu_dict.get(v)
            if self._otu is None:
                rich_logger.error(WarningCodes.REFERENCED_ID_NOT_FOUND,
                                  {'key': '@otu',
                                   'value': v},
                                  container=self)
    def get_parent(self):
        e = self._edge
        if e is None:
            return None
        return e._source
    def get_clade_if_tips_contained(self, avoid_child, tips_set):
        '''Returns bool, list of nodes in the clade
        True, list of all nodes in the clade (if all tips are in tip_set)
        False, None
        '''
        #@TEMP should not use recursion, here...
        if len(self._children) == 0:
            if self in tips_set:
                return True, [self]
            return False, None
        r = []
        for el in self._children:
            if el._target != avoid_child:
                b, c = el._target.get_clade_if_tips_contained(None, tips_set)
                if b:
                    r.extend(c)
                else:
                    return False, None
        r.append(self)
        return True, r
    def construct_path_to_root(self, encountered_nodes):
        n = self
        p = []
        s = set()
        while n:
            if n in s:
                return n, p
            if n in encountered_nodes:
                return None, []
            p.append(n)
            s.add(n)
            encountered_nodes.add(n)
            if n._edge:
                n = n._edge._source
            else:
                break
        return None, p

class Tree(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id', 'edge', 'node')
    EXPECETED_KEYS = ('@id',)
    PERMISSIBLE_KEYS = ('@id', '@about', 'node', 'edge', 'meta')
    EXPECTED_META_KEYS = ('ot:inGroupClade', 'ot:branchLengthMode', 'ot:tag')
    DELETE_ME_TAGS = ('delete', 'del', 'delet', 'delete', 'delete me', 'do not use')
    USE_ME_TAGS = ('choose me',)
    EXPECTED_TAGS = tuple(list(DELETE_ME_TAGS) + list(USE_ME_TAGS))
    TAG_CONTEXT = 'tree'
    def get_path_dict(self, subelement, prop_name):
        d = {
            'top': 'trees',
            'treesID': self._container.nexson_id,
            'treeID': self.nexson_id,
            'inMeta': False,
        }
        if subelement == 'meta':
            d['inMeta'] = True
        if prop_name:
            d['property'] = prop_name
        return d
    def __init__(self, o, rich_logger, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self.consume_meta_and_check_keys(o, rich_logger)
        self._ingroup= self.get_singelton_meta('ot:inGroupClade')
        k = 'ot:branchLengthMode'
        self._branch_len_mode = self.get_singelton_meta(k, warn_if_missing=False)
        if self._branch_len_mode is not None:
            if self._branch_len_mode not in ['ot:substitutionCount',
                                             'ot:changesCount',
                                             'ot:time',
                                             'ot:bootstrapValues',
                                             'ot:posteriorSupport']:
                if self._branch_len_mode in ['ot:other', 'ot:undefined']:
                    rich_logger.warn(WarningCodes.PROPERTY_VALUE_NOT_USEFUL,
                                     {'key': k,
                                      'value': self._branch_len_mode},
                                     container=self,
                                     subelement='meta')
                else:
                    rich_logger.error(WarningCodes.UNRECOGNIZED_PROPERTY_VALUE,
                                     {'key': k,
                                      'value': self._branch_len_mode},
                                      container=self,
                                      subelement='meta')
        self._tag_list = self.get_list_meta('ot:tag', warn_if_missing=False)
        if isinstance(self._tag_list, str) or isinstance(self._tag_list, unicode):
            self._tag_list = [self._tag_list]
        unexpected_tags = [i for i in self._tag_list if i.lower() not in self.EXPECTED_TAGS]
        for tag in unexpected_tags:
            rich_logger.warn(WarningCodes.UNRECOGNIZED_TAG, tag, container=self, subelement='meta')
        self._tagged_for_deletion = False
        self._tagged_for_inclusion = False # is there a tag meaning "use this tree?"
        tl = [i.lower() for i in self._tag_list]
        del_tag, inc_tag = None, None
        for t in Tree.DELETE_ME_TAGS:
            if t in tl:
                self._tagged_for_deletion = True
                del_tag = self._tag_list[tl.index(t)]
        for t in Tree.USE_ME_TAGS:
            if t in tl:
                self._tagged_for_inclusion = True
                inc_tag = self._tag_list[tl.index(t)]
        if self._tagged_for_inclusion and self._tagged_for_deletion:
            rich_logger.warn(WarningCodes.CONFLICTING_PROPERTY_VALUES,
                             [('ot:tag', del_tag), ('ot:tag', inc_tag)],
                             container=self,
                             subelement='meta')
        self._node_dict = {}
        self._node_list = []
        self._edge_dict = {}
        self._edge_list = []
        otu_collection = None
        if container is not None:
            otu_collection = container._otu_collection
        if otu_collection is None:
            otu_dict = {}
        else:
            otu_dict = otu_collection._as_dict
        v = o.get('node', [])
        self._root_node = None
        if not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, container=self, subelement='node')
        else:
            for el in v:
                n_node = Node(el, rich_logger, otu_dict, container=self)
                nid = n_node.nexson_id
                if nid is not None:
                    if nid in self._node_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, nid, container=self, subelement='node')
                    else:
                        self._node_dict[nid] = n_node
                self._node_list.append(n_node)
                if n_node._is_root:
                    if self._root_node is None:
                        self._root_node = n_node
                    else:
                        rich_logger.error(WarningCodes.MULTIPLE_ROOT_NODES, nid, container=self, subelement='node')
        if self._root_node is None:
            rich_logger.warn(WarningCodes.NO_ROOT_NODE, None, container=self)
        v = o.get('edge', [])
        if not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, container=self, subelement='edge')
        else:
            for el in v:
                n_edge = Edge(el, rich_logger, nodes=self._node_dict, container=self)
                eid = n_edge.nexson_id
                if eid is not None:
                    if eid in self._edge_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, eid, container=self, subelement='edge')
                    else:
                        self._edge_dict[eid] = n_edge
                self._edge_list.append(n_edge)
        # check the tree structure...
        lowest_node_set = set()
        encountered_nodes = set()
        ott_id2node = {}
        multi_labelled_ott_id = set()
        valid_tree = True
        for nd in self._node_list:
            cycle_node, path_to_root = nd.construct_path_to_root(encountered_nodes)
            if cycle_node:
                valid_tree = False
                rich_logger.error(WarningCodes.CYCLE_DETECTED, cycle_node, container=self)
            if path_to_root:
                lowest_node_set.add(path_to_root[-1])
            if len(nd._children) == 0:
                if nd._otu is None:
                    rich_logger.error(WarningCodes.TIP_WITHOUT_OTU, nd, container=nd)
                elif nd._otu._ott_id is None:
                    rich_logger.warn(WarningCodes.TIP_WITHOUT_OTT_ID, nd, container=nd)
                else:
                    nl = ott_id2node.setdefault(nd._otu._ott_id, [])
                    if len(nl) == 1:
                        multi_labelled_ott_id.add(nd._otu._ott_id)
                    nl.append(nd)
        for ott_id in multi_labelled_ott_id:
            tip_list = ott_id2node.get(ott_id)
            rich_logger.warn(WarningCodes.MULTIPLE_TIPS_MAPPED_TO_OTT_ID, 
                             {'ott_id': ott_id,
                              'node_list': tip_list},
                              container=self)

        if len(lowest_node_set) > 1:
            valid_tree = False
            lowest_node_set = [(i.nexson_id, i) for i in lowest_node_set]
            lowest_node_set.sort()
            lowest_node_set = [i[1] for i in lowest_node_set]
            rich_logger.error(WarningCodes.DISCONNECTED_GRAPH_DETECTED, lowest_node_set, container=self)
        elif len(lowest_node_set) == 1:
            ln = list(lowest_node_set)[0]
            if self._root_node is not None and self._root_node is not ln:
                rich_logger.error(WarningCodes.INCORRECT_ROOT_NODE_LABEL,
                                  {'tagged': self._root_node,
                                   'node_without_parent': ln},
                                  container=self)
        if valid_tree:
            for ott_id in multi_labelled_ott_id:
                tip_list = ott_id2node.get(ott_id)
                clade_tips = self.break_by_clades(tip_list)
                if len(clade_tips) > 1:
                    rich_logger.warn(WarningCodes.NON_MONOPHYLETIC_TIPS_MAPPED_TO_OTT_ID, 
                                     {'ott_id': ott_id, 'clades': clade_tips},
                                     container=self)
    def break_by_clades(self, tip_list):
        '''Takes a list of nodes. returns a list of lists. 
        Each sub list is a set of leaves in the tree that form the tips of a clade on the tree..
        '''
        c = list(tip_list)
        cs = set(c)
        if len(tip_list) < 2:
            return [c]
        clade_lists = []
        while len(c) > 0:
            n = c.pop(0)
            p = n.get_parent()
            assert p is not None
            next_el = [n]
            while p is not None:
                all_in_cs, des_nodes = p.get_clade_if_tips_contained(n, cs)
                if all_in_cs:
                    next_el.extend(des_nodes)
                    for d in des_nodes:
                        if d in cs:
                            c.remove(d)
                else:
                    break
                n = p
                p = p.get_parent()
            clade_lists.append(next_el)
        return clade_lists

class OTUCollection(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id', 'otu')
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = ('@id', 'otu')
    EXPECTED_META_KEYS = tuple()
    TAG_CONTEXT = 'otus'
    def get_path_dict(self, subelement, prop_name):
        d = {
            'top': 'otus',
            'otusID': self.nexson_id,
        }
        if subelement == 'meta':
            d['inMeta'] = True
        if prop_name:
            d['property'] = prop_name
        return d
    def __init__(self, o, rich_logger, container):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self._as_list = []
        self._as_dict = {}
        self.consume_meta_and_check_keys(o, rich_logger)
        v = o.get('otu', [])
        if not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, container=self, subelement='otu')
        else:
            for el in v:
                n_otu = OTU(el, rich_logger, container=self)
                nid = n_otu.nexson_id
                if nid is not None:
                    if nid in self._as_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, nid, container=self, subelement='otu')
                    else:
                        self._as_dict[nid] = n_otu
                self._as_list.append(n_otu)

class TreeCollection(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id', 'tree', '@otus')
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = ('@id', 'tree', '@otus')
    EXPECTED_META_KEYS = tuple()
    TAG_CONTEXT = 'trees'
    def get_path_dict(self, subelement, prop_name):
        d = {
            'top': 'trees',
            'treesID': self.nexson_id,
            'inMeta': False,
        }
        if subelement == 'meta':
            d['inMeta'] = True
        if prop_name:
            d['property'] = prop_name
        return d
    def __init__(self, o, rich_logger, container):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self._as_list = []
        self._as_dict = {}
        self.consume_meta_and_check_keys(o, rich_logger)
        self._otu_collection = None
        v = o.get('@otus')
        if v is not None:
            if container is None \
               or container.otus is None \
               or v != container.otus.nexson_id:
                rich_logger.error(WarningCodes.REFERENCED_ID_NOT_FOUND,
                                  {'key': '@otus',
                                   'value': v},
                                  container=self)
            else:
                self._otu_collection = container.otus
        v = o.get('tree', [])
        if not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, container=self, subelement='tree')
        else:
            for el in v:
                tree = Tree(el, rich_logger, container=self)
                tid = tree.nexson_id
                if tid is not None:
                    if tid in self._as_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, nid, container=self, subelement='tree')
                    else:
                        self._as_dict[tid] = tree
                self._as_list.append(tree)

class NexSON(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECETED_KEYS = ('@id', 'otus', 'trees', 'meta')
    PERMISSIBLE_KEYS = ('@about',
                     '@generator',
                     '@id',
                     '@nexmljson',
                     '@version',
                     '@xmlns',
                     'otus',
                     'trees',
                     'meta',
                     )
    EXPECTED_META_KEYS = ('ot:studyId', 
                          'ot:focalClade',
                          'ot:studyPublication',
                          'ot:studyYear',
                          'ot:curatorName', 
                          'ot:studyPublicationReference', 
                          'ot:dataDeposit',
                          'ot:tag')
    EXPECTED_TAGS = tuple()
    TAG_CONTEXT = 'nexml'
    def get_path_dict(self, subelement, prop_name):
        if subelement == 'meta':
            d = {
                'top': 'meta',
                'inMeta': True,
            }
        else: 
            d = {'inMeta':False}
        if prop_name:
            d['property'] = prop_name
        return d
    def __init__(self, o, rich_logger=None):
        '''Creates an object that validates `o` as a dictionary
        that represents a valid NexSON object.
        Warnings are errors will be passed to rich_logger (or 
        as new DefaultRichLogger if None is passed in)
        '''
        if rich_logger is None:
            rich_logger = DefaultRichLogger()
        self.otus = None
        self.trees = None
        NexsonDictWrapper.__init__(self, o, rich_logger, None)
        for k in o.keys():
            if k not in ['nexml']:
                rich_logger.warning(UnrecognizedKeyWarning(k, container=self))
        self._nexml = None
        if 'nexml' not in o:
            rich_logger.emit_error(MissingMandatoryKeyWarning('nexml', container=self, severity=SeverityCodes.ERROR))
            return ## EARLY EXIT!!
        self._nexml = o['nexml']

        check_key_presence(self._nexml, self, rich_logger)
        self._consume_meta(self._nexml, rich_logger, self.EXPECTED_META_KEYS)
        self._study_id = self.get_singelton_meta('ot:studyId')
        self._focal_clade_id = self.get_singelton_meta('ot:focalClade')
        self._study_publication = self.get_singelton_meta('ot:studyPublication')
        self._study_year = self.get_singelton_meta('ot:studyYear')
        self._curator_name = self.get_singelton_meta('ot:curatorName')
        self._data_deposit = self.get_singelton_meta('ot:dataDeposit')
        self._study_publication_reference = self.get_singelton_meta('ot:studyPublicationReference')
        self._tags = self.get_list_meta('ot:tag', warn_if_missing=False)
        if isinstance(self._tags, str) or isinstance(self._tags, unicode):
            self._tags = [self._tags]
        unexpected_tags = [i for i in self._tags if i not in self.EXPECTED_TAGS]
        for tag in unexpected_tags:
            rich_logger.warn(WarningCodes.UNRECOGNIZED_TAG, tag, container=self, subelement='meta')
        v = self._nexml.get('otus')
        if v is None:
            rich_logger.emit_error(MissingMandatoryKeyWarning('otus', container=self, severity=SeverityCodes.ERROR))
        else:
            self.otus = OTUCollection(v, rich_logger, container=self)
        v = self._nexml.get('trees')
        if v is None:
            rich_logger.emit_error(MissingMandatoryKeyWarning('tree', container=self, severity=SeverityCodes.ERROR))
        else:
            self.trees = TreeCollection(v, rich_logger, container=self)
            possible_trees = [t for t in self.trees._as_list if t._tagged_for_inclusion or (not t._tagged_for_deletion)]
            if len(possible_trees) > 1:
                rich_logger.warn(WarningCodes.MULTIPLE_TREES, self.trees._as_list, container=self.trees)
            elif len(possible_trees) == 0:
                rich_logger.warn(WarningCodes.NO_TREES, None, container=self.trees)


def indented_keys(out, o, indentation='', indent=2):
    next_indentation = indentation + (' '*indent)
    if isinstance(o, dict):
        key_list = o.keys()
        key_list.sort()
        #out.write('{i}{{\n'.format(i=indentation))
        for k in key_list:
            v = o[k]
            if isinstance(v, dict):
                out.write('{i}{k} :\n'.format(i=indentation, k=k))
                indented_keys(out, v, next_indentation, indent)
                out.write('{i}\n'.format(i=indentation))
            elif isinstance(v, list) or isinstance(v, tuple):
                out.write('{i}{k} :\n'.format(i=indentation, k=k))
                indented_keys(out, v, next_indentation, indent)
            else:
                if k == '@property':
                    out.write('{i}{k} : {v}\n'.format(i=indentation, k=k, v=v))
                else:
                    out.write('{i}{k}\n'.format(i=indentation, k=k))
        #out.write('{i}}}\n'.format(i=indentation))
    else:
        assert isinstance(o, list) or isinstance(o, tuple)
        has_sub_list = False
        sk = set()
        for el in o:
            if isinstance(el, list) or isinstance(el, tuple):
                has_sub_list = True
            else:
                sk.update(el.keys())
        key_list = list(sk)
        key_list.sort()
        out.write('{i}[\n'.format(i=indentation))
        if has_sub_list:
            for el in o:
                if isinstance(el, list) or isinstance(el, tuple):
                    indented_keys(out, el, next_indentation, indent)
        for k in key_list:
            out.write('{i}{k}\n'.format(i=next_indentation, k=k))
        out.write('{i}]\n'.format(i=indentation))
        

