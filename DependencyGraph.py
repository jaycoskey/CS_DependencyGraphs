#!/usr/bin/env python
# Copyright 2011 by Jay M. Coskey
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# import string
import sys

from datetime import timedelta

# Component attributes
START_KEY   = 'tstart'
STOP_KEY = 'tstop'

# Dependency attributes
COMPONENT_KEY = 'component_name'
REQUIREMENT_KEY  = 'required'

# Start/stop attributes
BEGIN_SHUTDOWN_KEY = 'beginShutdown'
BEGIN_STARTUP_KEY  = 'beginStartup'
END_SHUTDOWN_KEY   = 'endShutdown'
END_STARTUP_KEY    = 'endStartup'

def trace(trace_level = 1):
    def trace_decorator(func):
        """Print banners on entry and exit from wrapped function"""
        def tracedFunc(self, *args, **kwds):
            self.vprint(trace_level, '=' * 40) 
            self.vprint(trace_level, 'Entering %s' % func.__name__)
            result = func(self, *args, **kwds)
            self.vprint(trace_level, 'Exiting %s' % func.__name__)
            return result
        return tracedFunc
    return trace_decorator
        
class DependencyDirection(object):
    SHUTDOWN  = 1   # Walk the (directed) graph from "leaves" to roots.
    STARTUP   = 0   # Walk the (directed) graph from roots to "leaves".
    
class DependencyColor(object):
    WHITE = 0   # Not yet visited
    GRAY  = 1   # Being visited
    BLACK = 2   # Done being visited

class DependencyCycleException(Exception):
    """Represents a cycle among the dependencies,
    such as a -> a, or a -> b -> a, or a -> b -> c -> a."""
    def __init_(self, message=''):
        self.message = 'Error: Dependency cycle detected'
        if message != "":
            self.message += ': ' + message

class DependencyDuplicateComponentException(Exception):
    """Represents a component duplication.  Currently unneeded,
    since the data structure that is passed to the DependencyGraph's
    __init__ function is a Dictionary, which has unique keys."""
    def __init_(self, message=''):
        self.message = 'Error: Duplication of component node'
        if message != "":
            self.message += ': ' + message

class DependencyDuplicateDependencyException(Exception):
    """Represents a dependency duplication, such as having the dependency
    a -> b listed twice."""
    def __init_(self, message=''):
        self.message = 'Error: Duplication of dependency'
        if message != "":
            self.message += ': ' + message

class DependencyGraph(object):
    """Represents a dependency graph, with components indexed by name (a string).
    The storage of "roots", "leaves", and a tsorted list of node names
    allows traversal either down or up the dependency tree.
    """
    @trace(1)
    def __init__(self,
                 components=None,
                 dependencies=None,
                 is_strict=True,
                 verbosity=0):
        """@param: components: A dictionary of nodes, indexed by name,
            with start and stop times given as additional attributes,
            using keys START_KEY and STOP_KEY.
        @param: dependencies: A list of dependencies, each of which is
            a dictionary, with keys COMPONENT_KEY (the one depending on another),
            and REQUIREMENT_KEY (the component that is depended upon).
        @param: is_strict: If True, an exception is thrown if cycles exist.
            Otherwise, enough dependencies are "rejected" until the graph is acyclic.
        @param: verbosity: A non-negative integer that controls the level of verbosity
            of the DependencyGraph functions.
        @throws DependencyCycleException
        @throws ValueError"""
        self.nodesByName = {}
        self.rootsByName = {}
        self.leavesByName = {}
        self.startStopInfoByName = {}
        self.start_tsorted_names = []
        self.rejected_dependencies = []  # For remediation of cycles
        self.is_strict = is_strict
        self.verbosity = verbosity
        
        if not components and not dependencies:
            pass
        self.init_nodes(components)
        self.vprint(2, 'Number of nodes = %d' % len(self.nodesByName))
        self.vprint_nodes(2)

        self.init_edges(dependencies)
        self.vprint(2, 'Number of edges = %d' % self.num_edges())
        self.vprint_edges(2)
        self.init_check_for_cycles()
        if self.rejected_dependencies and verbosity >= 1:
            self.vprint(2, 'Number of edges after removing cycles = %d'
                        % self.num_edges())
            self.vprint_edges(2)
        if verbosity > 10:
            print(self.xml_str(2))
            
    def __repr__(self):
        """Return an XML element containing the id of the object.  See xml_str()."""
        return "<DependencyGraph id ='{}'/>".format(id(self))

    def __str__(self):
        """Return an XML element containing the root nodes of the object.  See xml_str()."""
        result = "<DependencyGraph id='{}'>\n".format(id(self))
        for name in self.rootsByName.keys():
            result += "<DependencyNode isRoot='true' name='{}'/>\n".format(name)
        result += "</DependencyGraph>\n"
        return result
        
    def add_node(self, name, attributes):
        """Add a DependencyNode to this DependencyGraph.
        @throws ValueError if a node name is duplicated.  (Note: This currently cannot happen.)"""
        if name in self.nodesByName.keys():
            raise ValueError('Attempt to duplicate component identifier "%s"'
                             % name)
        node = DependencyNode(name, attributes)
        self.nodesByName[name] = node
        return node

    @trace(1)
    def init_check_for_cycles(self):
        """Calls the function init_check_for_cycles_graph() for each root node.
        Detects and removes cycles if self.is_strict == False.
        This function also sets the attribute tsorted_node_names.
        @throws DependencyCycleException"""
        roots = list(self.rootsByName.values())
        # roots = sorted(roots)
        nodeColorByName = {}
        for name in self.nodesByName.keys():
            nodeColorByName[name] = DependencyColor.WHITE
        indegreeByName = dict([
            (name, len(node.parents.keys()))
            for name, node in self.nodesByName.items()
            ])
        for root in roots:
            self.init_check_for_cycles_roots([root], nodeColorByName, indegreeByName)
        unvisited_node_names = [name for name in self.nodesByName.keys()
                                if nodeColorByName[name] == DependencyColor.WHITE]
        self.vprint(1, 'Number of unvisited nodes='
                    + str(len(unvisited_node_names)))
        if unvisited_node_names:
            if self.is_strict:
                raise DependencyCycleException(
                    'One or more cycles exist among the following nodes: '
                        + str(unvisited_node_names))
            else:  # Remove incoming edges to remove cycle
                while len(unvisited_node_names) > 0:
                    unvisited_node_name = unvisited_node_names.pop()
                    unvisited_node = self.nodesByName[unvisited_node_name]
                    parent_names = unvisited_node.parents.keys()
                    for parent_name in list(parent_names):
                        del unvisited_node.parents[parent_name]
                        del self.nodesByName[parent_name].children[unvisited_node_name]
                        self.vprint(1, 'Removing cycle-causing edge: {} -> {}'.format(
                            parent_name, unvisited_node_name))
                        self.rejected_dependencies.append(
                            (parent_name, unvisited_node_name))
                    self.vprint(1, 'Adding root node "%s"'
                                % str(unvisited_node_name))
                    self.rootsByName[unvisited_node_name] = unvisited_node
                    self.init_check_for_cycles_roots(
                        [self.nodesByName[unvisited_node_name]],
                        nodeColorByName,
                        indegreeByName
                        )
                    unvisited_node_names = [
                        name for name in self.nodesByName.keys()
                        if nodeColorByName[name] == DependencyColor.WHITE
                        ]
        leaf_names = self.leavesByName.keys()
        # leaf_names = sorted(leaf_names)
        self.vprint(2, 'Leaf nodes: ' + ', '.join(leaf_names))
        self.leavesByName = dict(
                [(leaf_name, leaf) for leaf_name, leaf in self.nodesByName.items()
                    if not leaf.children]
            )

    @trace(3)  # Higher min_verbosity because this is called for each node
    def init_check_for_cycles_roots(self, roots, nodeColorByName, indegreeByName):
        """Together with init_check_for_cycles(), checks the DependencyGraph for cycles.
        Uses graph coloring (white, gray, black) to trace node state,
        and the dictionary instance indegreeByName
        to track when all parents of a node have been inspected.
        @throws DependencyCycleException"""
        for root in roots:
            nodeColorByName[root.name] = DependencyColor.GRAY
            self.vprint(2, 'Appending %s to the tsorted list of node names' % root.name)
            self.start_tsorted_names.append(root.name)
        while roots:
            root = roots.pop(0)
            nodeColorByName[root.name] = DependencyColor.GRAY
            
            childrenToBeDeletedByName = {}
            for child_name, child in root.children.items():
                child_node_color = nodeColorByName[child_name]
                if child_node_color == DependencyColor.WHITE:
                    indegreeByName[child_name] -= 1
                    if indegreeByName[child_name] == 0:
                        self.start_tsorted_names.append(child_name)
                        roots.append(child)
                if child_node_color == DependencyColor.GRAY:
                    if self.is_strict:
                        raise DependencyCycleException('Back-edge found')
                    else:
                        self.vprint(1,
                                    'Removed back-edge: "{}" --> "{}"'.format(
                                    root.name,
                                    child_name))
                        childrenToBeDeletedByName[child_name] = child
            for child_name, child in childrenToBeDeletedByName.items():
                # Unlink parent and child
                del child.parents[root.name]
                del root.children[child_name]
                self.rejected_dependencies.append((root.name, child_name))
            nodeColorByName[root.name] = DependencyColor.BLACK
        
    @trace(1)
    def init_edges(self, dependencies):
        """Initialize the edges of the DependencyGraph.  Called by __init__().
        Note that this function does not check for cycles.
        That is done by init_check_for_cycles.
        @throws ValueError"""
        for dep in dependencies:
            comp_name = dep[COMPONENT_KEY]
            if comp_name not in self.nodesByName.keys():
                raise ValueError('Dependency has unknown component ("%s")'
                                 % comp_name)
            req_name = dep[REQUIREMENT_KEY]
            if req_name not in self.nodesByName.keys():
                raise ValueError('Dependecy on unknown component ("%s")'
                                 % req_name)
            comp = self.nodesByName[dep[COMPONENT_KEY]]
            req = self.nodesByName[dep[REQUIREMENT_KEY]]
            if req_name in comp.children.keys():
                raise DependencyDuplicateDependencyException(
                    '(' + comp_name + ' --> ' + req_name + ')'
                    )
            # Link parent and child
            self.vprint(2, 'Adding the edge {} -> {}'.format(comp_name, req_name))
            comp.children[req_name] = req
            req.parents[comp_name] = comp
    
        root_names = [name for name, node in self.nodesByName.items()
                      if not node.parents]
        root_names_string = ''
        if root_names:
            # root_name = sorted(root_names)
            root_names_string += ', '.join(root_names)
        else:
            root_names_string += 'None'
        self.vprint(2, 'Initial root nodes: ' + root_names_string)
        for root_name in root_names:
            self.rootsByName[root_name] = self.nodesByName[root_name]

    @trace(1)
    def init_nodes(self, components):
        """Initialize the nodes of the DependencyGraph.  Called by __init__()."""
        for name in components.keys():
##            # The following exception below can never be thrown,
##            # since the "components" argument has unique keys.
##            if name in self.nodesByName.keys():
##                DependencyDuplicateComponentException('(' + name + ')')
            self.add_node(name, components[name])

    def num_edges(self):
        result = 0
        for name, node in self.nodesByName.items():
            result += len(node.children)
        return result

    def num_nodes(self):
        return len(self.nodesByName.keys())

    @trace(2)
    def set_startStopInfoByName(self,
                                dependency_direction=DependencyDirection.STARTUP):
        """Determines the times that the components (nodes) in the DependencyGraph
        can be started/stopped, relative to an arbitrary starting/stopping time,
        while respecting dependencies of components on others.
        @throws ValueError"""
        dg_strategy = {}        
        if dependency_direction == DependencyDirection.STARTUP:
            # Traverse down the dependency graph,\
            #   basing beginning of startup on the end of startup of other components.
            dg_strategy['tsorted_names'] = self.start_tsorted_names
            dg_strategy['get_parents']   = lambda node: node.parents
            dg_strategy['REF_KEY']       = END_STARTUP_KEY
            dg_strategy['ref_time_extremum'] = max
        else:
            # Traverse up the dependency graph,
            #   basing end of shutdown on the beginning of shutdown of other components.
            dg_strategy['tsorted_names'] = reversed(self.start_tsorted_names)
            dg_strategy['get_parents']   = lambda node: node.children
            dg_strategy['REF_KEY']       = BEGIN_SHUTDOWN_KEY
            dg_strategy['ref_time_extremum'] = min

        for name in dg_strategy['tsorted_names']:
            if name not in self.startStopInfoByName.keys():
                self.startStopInfoByName[name] = {}
            parent_names = dg_strategy['get_parents'](self.nodesByName[name]).keys()
            reference_time = timedelta(minutes=0)
            if parent_names:
                parent_reference_times = list(map(
                    lambda parent_name:
                    self.startStopInfoByName[parent_name][dg_strategy['REF_KEY']],
                    parent_names
                    ))
                reference_time = dg_strategy['ref_time_extremum'](
                    parent_reference_times,
                    key=lambda td: td.days + 86400 * td.seconds
                    )
            node = self.nodesByName[name]
            if dependency_direction == DependencyDirection.STARTUP:
                self.startStopInfoByName[name].update({
                    BEGIN_STARTUP_KEY  : reference_time,
                    END_STARTUP_KEY    : reference_time + node.attributes[START_KEY]
                    })
            elif dependency_direction == DependencyDirection.SHUTDOWN:
                self.startStopInfoByName[name].update({
                    BEGIN_SHUTDOWN_KEY : reference_time - node.attributes[STOP_KEY],
                    END_SHUTDOWN_KEY   : reference_time
                    })
            else:
                raise ValueError('Unknown DependencyDirection value, %s'
                                 % dependency_direction)

    def vprint(self, min_verbosity, *args, **kwds):
        # self.verbosity is not yet defined in the annotated copy of __init__.
        if hasattr(self, 'verbosity') and self.verbosity >= min_verbosity:
            nspaces = max(0, 2 * (min_verbosity - 1))
            indent = ' ' * nspaces
            return print('INFO({}): {}'.format(min_verbosity, indent), *args, **kwds)
    
    def vprint_edges(self, min_verbosity, header='Edges: ', sep=", "):
        content = header
        if self.verbosity >= min_verbosity:
            edge_names = [node.name + ' --> ' + req.name
                          for node in self.nodesByName.values()
                          for req in node.children.values()]
            if edge_names:
                content += sep.join(edge_names)
            else:
                content += 'None'
        return self.vprint(min_verbosity, content)
    
    def vprint_nodes(self, min_verbosity, header='Nodes: ', sep=', '):
        content = header
        if self.verbosity >= min_verbosity:
            if self.nodesByName:
                node_names = [repr(node) for node in self.nodesByName.values()]
                # node_names = sorted(node_names)
                content += sep.join(node_names)
            else:
                content += 'None'
        return self.vprint(min_verbosity, content)
        
    def xml_str(self,
                indent=0,
                roots=None,
                get_childrenByName=None,
                get_attrDictByName=lambda name: {},
                attr_keys=[]):
        """Return XML showing the DependencyGraph and all its DependencyNodes.
        By default, the graph is shown in top-down order, but that can be overridden
        by use of the "roots" and "get_children" arguments.
        Also, additional DependencyNode attributes can be displayed by use of the
        "get_attrDictByName" and "attr_keys" arguments.
        """
        if roots == None:
            roots = self.rootsByName.values()
        prefix = " " * indent
        result = prefix + "<DependencyGraph>\n"
        # roots = sorted(roots, key=lambda node: node.name)
        for root in roots:
            result += root.xml_str(indent + 2,
                                   get_childrenByName=get_childrenByName,
                                   attr_keys=attr_keys,
                                   get_attrDictByName=get_attrDictByName)
        result += prefix + "</DependencyGraph>\n"
        return result
    
class DependencyNode(object):
    """This class stores the topology of the DependencyGraph
    through its "parents" and "children" attributes.
    It also stores properties of the given node though its "attribute" attribute."""
    def __init__(self, name, attributes):
        """Copy node properties from the "attributes" argument.
        The "parents" and "children" attributes are initialized later,
        through the DependencyGraph.__init__()."""
        self.name = name
        self.attributes = attributes
        self.parents = {}
        self.children = {}

    def __repr__(self):
        return self.name

    def __str__(self):
        return "<DependencyNode name='" + self.name + "'/>\n"  

    def xml_str(self,
                indent=0,
                get_childrenByName=None,
                get_attrDictByName=lambda name: {},
                attr_keys=[]):
        """@see DependencyGraph.xml_str()."""
        if get_childrenByName == None:
            get_childrenByName = lambda node: node.children.values()
        prefix = " " * indent
        result = prefix + "<DependencyNode name='" + self.name \
                 + "' id='" + str(id(self)) + "'"
        if get_attrDictByName(self.name):
            for attr_key in attr_keys:
                result += " {}='{}' ".format(
                    attr_key,
                    get_attrDictByName(self.name)[attr_key])
        if get_childrenByName(self):
            result += ">\n"
            children = get_childrenByName(self)
            # children = sorted(get_childrenByName(self), key=lambda node: node.name)
            for child in children:
                result += child.xml_str(indent + 2,
                                        get_childrenByName,
                                        get_attrDictByName=get_attrDictByName,
                                        attr_keys=attr_keys)
            result += prefix + "</DependencyNode>\n"
        else:
            result += "/>\n"
        return result
    
if __name__=='__main__':
    ########################################
    # Dependency dgraph data
    ########################################
    comps = {
        'a': {START_KEY: timedelta(minutes=1),
              STOP_KEY: timedelta(minutes=1)
            },
        'b': {
            START_KEY: timedelta(minutes=2),
            STOP_KEY: timedelta(minutes=2)
            },
        'c': {
            START_KEY: timedelta(minutes=4),
            STOP_KEY: timedelta(minutes=4)
            },
        'x': {
            START_KEY: timedelta(minutes=8),
            STOP_KEY: timedelta(minutes=8)
            },
        'y': {
            START_KEY: timedelta(minutes=16),
            STOP_KEY: timedelta(minutes=16)
            },
        'z': {
            START_KEY: timedelta(minutes=32),
            STOP_KEY: timedelta(minutes=32)
           }
        }

    deps = [
        {COMPONENT_KEY: 'a', REQUIREMENT_KEY: 'x'},
        {COMPONENT_KEY: 'a', REQUIREMENT_KEY: 'y'},
        {COMPONENT_KEY: 'b', REQUIREMENT_KEY: 'x'},
        {COMPONENT_KEY: 'x', REQUIREMENT_KEY: 'y'},
        {COMPONENT_KEY: 'x', REQUIREMENT_KEY: 'z'},

        {COMPONENT_KEY: 'c', REQUIREMENT_KEY: 'c'},
    ]

    ########################################
    # Creation of dependency dgraph
    # (and display, if verbosity > 0)
    ########################################
    dgraph = DependencyGraph(comps, deps, is_strict=False, verbosity=0)

    ########################################
    # Display of dependency dgraph
    ########################################
    print('Here is the dependency dgraph, with node attributes:')
    print(dgraph.xml_str(2,
                roots=None,
                get_childrenByName=None,
                get_attrDictByName=lambda name: dgraph.nodesByName[name].attributes,
                attr_keys=[START_KEY, STOP_KEY])
          )
    print('Here are dependencies that were dropped to resolve dependency cycles:')
    if dgraph.rejected_dependencies:
        sys.stdout.write('\t')
        print(dgraph.rejected_dependencies, sep='\n\t')
    else:
        print('\tNone')
    print()
    print('Here is a topologically sorted node order: %s'
          % dgraph.start_tsorted_names)

    ########################################
    # Display of inverted dependency dgraph
    ########################################
    print()
    print('Here is the inverted dependency dgraph, without node attributes:')
    print(dgraph.xml_str(2, roots=dgraph.leavesByName.values(),
                       get_childrenByName=lambda x: x.parents.values()))
    
    ########################################
    # Compute & display startup times
    ########################################
    dgraph.set_startStopInfoByName()
    print('Startup times sorted by beginning of startup (commencement at 00:00):')
    for node_name in sorted(dgraph.start_tsorted_names,
                            key=lambda name:
                            dgraph.startStopInfoByName[name][BEGIN_STARTUP_KEY],
                            reverse=False):
        print('{:>9}: {:>20} -> {:>20}'.format(
            node_name,
            dgraph.startStopInfoByName[node_name][BEGIN_STARTUP_KEY],
            dgraph.startStopInfoByName[node_name][END_STARTUP_KEY]
            )
        )

    ########################################
    # Compute & display shutdown times
    ########################################
    print()
    dgraph.set_startStopInfoByName(dependency_direction=DependencyDirection.SHUTDOWN)
    print('Shutdown times sorted by beginning of shutdown (completion at 00:00):')
    for node_name in sorted(dgraph.start_tsorted_names,
                            key=lambda name:
                            dgraph.startStopInfoByName[name][BEGIN_SHUTDOWN_KEY],
                            reverse=True):
        print('{:>9}: {:>20} -> {:>20}'.format(
            node_name,
            dgraph.startStopInfoByName[node_name][BEGIN_SHUTDOWN_KEY],
            dgraph.startStopInfoByName[node_name][END_SHUTDOWN_KEY]
            )
        )
