#!/usr/bin/env python
import sys
from cStringIO import StringIO

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
              ]
for _n, _f in enumerate(WarningCodes.facets):
    setattr(WarningCodes, _f, _n)

def write_warning(out, prefix, wc, data, context=None):
    if not out:
        return
    if wc == WarningCodes.MISSING_MANDATORY_KEY:
        out.write('{p}Missing required key "{k}"'.format(p=prefix, k=data))
    elif wc == WarningCodes.MISSING_OPTIONAL_KEY:
        out.write('{p}Missing optional key "{k}"'.format(p=prefix, k=data))
    elif wc == WarningCodes.UNRECOGNIZED_KEY:
        out.write('{p}Unrecognized key "{k}"'.format(p=prefix, k=data))
    elif wc == WarningCodes.MISSING_LIST_EXPECTED:
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
        out.write('{p}Tip node ("{n}") without a valid @otu value'.format(p=prefix, n=data.nexson_id))
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
    if context is not None:
        out.write(' in "{el}"'.format(el=context))
    out.write('\n')

class DefaultRichLogger(object):
    def __init__(self):
        self.out = sys.stderr
        self.prefix = ''
    def warn(self, warning_code, data, context=None):
        write_warning(self.out, self.prefix, warning_code, data, context)
    def error(self, warning_code, data, context=None):
        s = StringIO()
        write_warning(s, self.prefix, warning_code, data, context)
        raise NexSONError(s.getvalue())

class ValidationLogger(DefaultRichLogger):
    def __init__(self):
        DefaultRichLogger.__init__(self)
        self.warnings = []
        self.errors = []
    def warn(self, warning_code, data, context=None):
        s = StringIO()
        write_warning(s, self.prefix, warning_code, data, context)
        self.warnings.append(s.getvalue())
    def error(self, warning_code, data, context=None):
        s = StringIO()
        write_warning(s, self.prefix, warning_code, data, context)
        self.errors.append(s.getvalue())

def check_key_presence(d, schema, rich_logger):
    '''Issues errors if `d` does not contain keys in the schema.PERMISSIBLE_KEYS iterable,
    warnings if `d` lacks keys listed in schema.EXPECETED_KEYS, or if `d` contains
    keys not listed in schema.PERMISSIBLE_KEYS.
    schema.get_tag_context() is used to tag any warning/errors
    '''
    for k in d.keys():
        if k not in schema.PERMISSIBLE_KEYS:
            rich_logger.warn(WarningCodes.UNRECOGNIZED_KEY, k, context=schema.get_tag_context())
    for k in schema.EXPECETED_KEYS:
        if k not in d:
            rich_logger.warn(WarningCodes.MISSING_OPTIONAL_KEY, k, context=schema.get_tag_context())
    for k in schema.REQUIRED_KEYS:
        if k not in d:
            rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, k, context=schema.get_tag_context())


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
    def get_nexson_id(self):
        return self._raw.get('@id')
    nexson_id = property(get_nexson_id)
    def get_tag_context(self):
        return '{f}(id={i})'.format(f=self.TAG_CONTEXT, i=self.nexson_id)
    def _consume_meta(self, o):
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

    def get_singelton_meta(self, property_name):
        v = self._meta2value.get(property_name)
        if v is None:
            self._logger.warn(WarningCodes.MISSING_OPTIONAL_KEY, '@property=' + property_name, context='meta in ' + self.get_tag_context())
        elif isinstance(v, MetaValueList):
            self._logger.error(WarningCodes.DUPLICATING_SINGLETON_KEY, '@property=' + property_name, context='meta in ' + self.get_tag_context())
        return v

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
    property_name = property(get_property_name)
    def get_property_value(self):
        return self._raw.get('$')
    value = property(get_property_value)

OTUMeta = Meta

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
    if not isinstance(m, list):
        rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, context='meta in ' + container.get_tag_context())
    else:
        for el in m:
            meta_el = Meta(el, rich_logger, container=container)
            meta_list.append(meta_el)
            mk = meta_el.property_name
            v = meta_el.value
            cv = to_meta_value.setdefault(mk, v)
            if cv is not v:
                if not isinstance(cv, MetaValueList):
                    to_meta_value[mk] = MetaValueList([cv, v])
                else:
                    to_meta_value.append(v)
            to_meta_list.setdefault(mk, []).append(meta_el)
    return (meta_list, to_meta_value, to_meta_list)

class OTU(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECETED_KEYS = ('@id',)
    PERMISSIBLE_KEYS = ('@id', '@about', '@label', 'meta')
    TAG_CONTEXT = 'otu'
    def __init__(self, o, rich_logger, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        check_key_presence(o, self, rich_logger)
        self._consume_meta(o)
        self._ott_id = self.get_singelton_meta('ot:ottolid')
        self._original_label = self.get_singelton_meta('ot:originalLabel')

class Edge(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id', '@source', '@target')
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = REQUIRED_KEYS
    TAG_CONTEXT = 'edge'
    def __init__(self, o, rich_logger, nodes, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        check_key_presence(o, self, rich_logger)
        self._source = None
        self._target = None
        sid = o.get('@source')
        if sid is not None:
            self._source = nodes.get(sid)
            if self._source is None:
                rich_logger.error(WarningCodes.REFERENCED_ID_NOT_FOUND,
                                  {'key': '@source',
                                   'value': sid},
                                  context=self.get_tag_context())
            else:
                self._source._children.append(self)
        tid = o.get('@target')
        if tid is not None:
            self._target = nodes.get(tid)
            if self._target is None:
                rich_logger.error(WarningCodes.REFERENCED_ID_NOT_FOUND,
                                  {'key': '@target',
                                   'value': tid},
                                  context=self.get_tag_context())
            elif self._target._edge is not None:
                rich_logger.error(WarningCodes.MULTIPLE_EDGES_FOR_NODES, 
                                  {'node': self._target,
                                  'edge': self
                                  }, 
                                  context=self.get_tag_context())
            else:
                self._target._edge = self


class Node(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = ('@id', '@otu', '@root')
    TAG_CONTEXT = 'node'
    def __init__(self, o, rich_logger, otu_dict, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        check_key_presence(o, self, rich_logger)
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
                                  context=self.get_tag_context())

    def construct_path_to_root(self, encountered_nodes):
        n = self
        p = []
        s = set()
        while n:
            #print 'cp2r ', n.nexson_id
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
    TAG_CONTEXT = 'tree'
    def __init__(self, o, rich_logger, container=None):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        check_key_presence(o, self, rich_logger)
        self._consume_meta(o)
        self._ingroup= self.get_singelton_meta('ot:inGroupClade')
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
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, context='node in ' + self.get_tag_context())
        else:
            for el in v:
                n_node = Node(el, rich_logger, otu_dict, container=self)
                nid = n_node.nexson_id
                if nid is not None:
                    if nid in self._node_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, nid, context='node in ' + self.get_tag_context())
                    else:
                        self._node_dict[nid] = n_node
                self._node_list.append(n_node)
                if n_node._is_root:
                    if self._root_node is None:
                        self._root_node = n_node
                    else:
                        rich_logger.error(WarningCodes.MULTIPLE_ROOT_NODES, nid, context='node in ' + self.get_tag_context())
        if self._root_node is None:
            rich_logger.warn(WarningCodes.NO_ROOT_NODE, None, self.get_tag_context())
        v = o.get('edge', [])
        if not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, context='edge in ' + self.get_tag_context())
        else:
            for el in v:
                n_edge = Edge(el, rich_logger, nodes=self._node_dict, container=self)
                eid = n_edge.nexson_id
                if eid is not None:
                    if eid in self._edge_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, eid, context='edge in ' + self.get_tag_context())
                    else:
                        self._edge_dict[eid] = n_edge
                self._edge_list.append(n_edge)
        lowest_node_set = set()
        encountered_nodes = set()
        for nd in self._node_list:
            cycle_node, path_to_root = nd.construct_path_to_root(encountered_nodes)
            #print cycle_node, [i.nexson_id for i in path_to_root], [i.nexson_id for i in encountered_nodes], [i.nexson_id for i in lowest_node_set]
            if cycle_node:
                rich_logger.error(WarningCodes.CYCLE_DETECTED, cycle_node, context='node in ' + self.get_tag_context())
            if path_to_root:
                lowest_node_set.add(path_to_root[-1])
            if len(nd._children) == 0 and nd._otu is None:
                rich_logger.error(WarningCodes.TIP_WITHOUT_OTU, nd, context=self.get_tag_context())
        if len(lowest_node_set) > 1:
            lowest_node_set = [(i.nexson_id, i) for i in lowest_node_set]
            lowest_node_set.sort()
            lowest_node_set = [i[1] for i in lowest_node_set]
            rich_logger.error(WarningCodes.DISCONNECTED_GRAPH_DETECTED, lowest_node_set, context=self.get_tag_context())
        elif len(lowest_node_set) == 1:
            ln = list(lowest_node_set)[0]
            if self._root_node is not None and self._root_node is not ln:
                rich_logger.error(WarningCodes.INCORRECT_ROOT_NODE_LABEL,
                                  {'tagged': self._root_node,
                                   'node_without_parent': ln},
                                  context=self.get_tag_context())

class OTUCollection(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id', 'otu')
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = ('@id', 'otu')
    TAG_CONTEXT = 'otus'
    def __init__(self, o, rich_logger, container):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self._as_list = []
        self._as_dict = {}
        check_key_presence(o, self, rich_logger)
        self._consume_meta(o)
        v = o.get('otu', [])
        if not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, context='otu in ' + self.get_tag_context())
        else:
            for el in v:
                n_otu = OTU(el, rich_logger, container=self)
                nid = n_otu.nexson_id
                if nid is not None:
                    if nid in self._as_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, nid, context='otu')
                    else:
                        self._as_dict[nid] = n_otu
                self._as_list.append(n_otu)

class TreeCollection(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id', 'tree', '@otus')
    EXPECETED_KEYS = tuple()
    PERMISSIBLE_KEYS = ('@id', 'tree', '@otus')
    TAG_CONTEXT = 'trees'
    def __init__(self, o, rich_logger, container):
        NexsonDictWrapper.__init__(self, o, rich_logger, container)
        self._as_list = []
        self._as_dict = {}
        check_key_presence(o, self, rich_logger)
        self._consume_meta(o)
        self._otu_collection = None
        v = o.get('@otus')
        if v is not None:
            if container is None \
               or container.otus is None \
               or v != container.otus.nexson_id:
                rich_logger.error(WarningCodes.REFERENCED_ID_NOT_FOUND,
                                  {'key': '@otus',
                                   'value': v},
                                  context='trees')
            else:
                self._otu_collection = container.otus
        v = o.get('tree', [])
        if not isinstance(v, list):
            rich_logger.error(WarningCodes.MISSING_LIST_EXPECTED, v, context='tree in ' + self.get_tag_context())
        else:
            for el in v:
                tree = Tree(el, rich_logger, container=self)
                tid = tree.nexson_id
                if tid is not None:
                    if tid in self._as_dict:
                        rich_logger.error(WarningCodes.REPEATED_ID, nid, context='tree')
                    else:
                        self._as_dict[tid] = tree
                self._as_list.append(tree)

class NexSON(NexsonDictWrapper):
    REQUIRED_KEYS = ('@id',)
    EXPECETED_KEYS = ('@id', 'otus', 'trees', 'meta')
    PERMISSIBLE_KEYS = ("@about",
                     "@generator",
                     "@id",
                     "@nexmljson",
                     "@version",
                     "@xmlns",
                     "otus",
                     "trees",
                     "meta",
                     )
    TAG_CONTEXT = 'nexml'
    def __init__(self, o, rich_logger=None):
        '''Creates an object that validates `o` as a dictionary
        that represents a valid NexSON object.
        Warnings are errors will be passed to rich_logger (or 
        as new DefaultRichLogger if None is passed in)
        '''
        if rich_logger is None:
            rich_logger = DefaultRichLogger()
        NexsonDictWrapper.__init__(self, o, rich_logger, None)
        for k in o.keys():
            if k not in ['nexml']:
                rich_logger.warn(WarningCodes.UNRECOGNIZED_KEY, k)
        self._nexml = None
        if 'nexml' not in o:
            rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, 'nexml')
            return ## EARLY EXIT!!
        self._nexml = o['nexml']
        check_key_presence(self._nexml, self, rich_logger)
        self._consume_meta(self._nexml)
        self._study_id = self.get_singelton_meta('ot:studyId')
        v = self._nexml.get('otus')
        if v is None:
            rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, 'otus', context='nexml')
            self.otus = None
        else:
            self.otus = OTUCollection(v, rich_logger, container=self)
        v = self._nexml.get('trees')
        if v is None:
            rich_logger.error(WarningCodes.MISSING_MANDATORY_KEY, 'tree', context='nexml')
        else:
            self.trees = TreeCollection(v, rich_logger, container=self)


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
        

