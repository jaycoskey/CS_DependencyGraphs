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

# TODO: JMC: Add tests to validate startup & shutdown times

from datetime import timedelta
import DependencyGraph
import unittest

class EmptyGraph(unittest.TestCase):
    def setUp(self):
        comps = {}
        deps = []
        self.dgraph = DependencyGraph.DependencyGraph(comps, deps, verbosity=0)
    def test_num_edges(self):
        self.assertTrue(self.dgraph.num_edges() == 0)
    def test_num_nodes(self):
        self.assertTrue(self.dgraph.num_nodes() == 0)

class OneNodeCycle(object):
    def __init__(self):
        self.comps = {
            'a': {DependencyGraph.START_KEY: timedelta(minutes=1),
                      DependencyGraph.STOP_KEY: timedelta(minutes=1)},
            }
        self.deps = [{DependencyGraph.COMPONENT_KEY: 'a',
                 DependencyGraph.REQUIREMENT_KEY: 'a'}]
        
class OneNodeCycleNonStrict(unittest.TestCase):
    def setUp(self):
        self.onc = OneNodeCycle()
        self.dgraph = DependencyGraph.DependencyGraph(
            self.onc.comps,
            self.onc.deps,
            is_strict=False,
            verbosity=0)
    def test_num_edges(self):
        self.assertTrue(self.dgraph.num_edges() == 0)
    def test_num_nodes(self):
        self.assertTrue(self.dgraph.num_nodes() == 1)

class OneNodeCycleStrict(unittest.TestCase):
    def setUp(self):
        self.onc = OneNodeCycle()
    def test_cycle_exception(self):
        self.assertRaises(DependencyGraph.DependencyCycleException,
                          DependencyGraph.DependencyGraph,
                          self.onc.comps,
                          self.onc.deps,
                          is_strict=True,
                          verbosity=0)

class ThreeNodeChain(unittest.TestCase):
    def setUp(self):
        comps = {
            'a': {DependencyGraph.START_KEY: timedelta(minutes=1),
                      DependencyGraph.STOP_KEY: timedelta(minutes=1)},
            'b': {DependencyGraph.START_KEY: timedelta(minutes=2),
                      DependencyGraph.STOP_KEY: timedelta(minutes=2)},
            'c': {DependencyGraph.START_KEY: timedelta(minutes=4),
                      DependencyGraph.STOP_KEY: timedelta(minutes=4)}
        }
        deps = [
            {DependencyGraph.COMPONENT_KEY: 'a',
                 DependencyGraph.REQUIREMENT_KEY: 'b'},
            {DependencyGraph.COMPONENT_KEY: 'b',
                 DependencyGraph.REQUIREMENT_KEY: 'c'},
        ]
        self.dgraph = DependencyGraph.DependencyGraph(comps, deps, verbosity=0)
    def test_num_edges(self):
        self.assertTrue(self.dgraph.num_edges() == 2)
    def test_num_nodes(self):
        self.assertTrue(self.dgraph.num_nodes() == 3)

class ThreeNodeCycle(object):
    def __init__(self):
        self.comps = {
            'a': {DependencyGraph.START_KEY: timedelta(minutes=1),
                      DependencyGraph.STOP_KEY: timedelta(minutes=1)},
            'b': {DependencyGraph.START_KEY: timedelta(minutes=2),
                      DependencyGraph.STOP_KEY: timedelta(minutes=2)},
            'c': {DependencyGraph.START_KEY: timedelta(minutes=4),
                      DependencyGraph.STOP_KEY: timedelta(minutes=4)},
            }
        self.deps = [
            {DependencyGraph.COMPONENT_KEY: 'a',
                 DependencyGraph.REQUIREMENT_KEY: 'b'},
            {DependencyGraph.COMPONENT_KEY: 'b',
                 DependencyGraph.REQUIREMENT_KEY: 'c'},
            {DependencyGraph.COMPONENT_KEY: 'c',
                 DependencyGraph.REQUIREMENT_KEY: 'a'},
            ]
    
class ThreeNodeCycleNonStrict(unittest.TestCase):
    def setUp(self):
        self.tnc = ThreeNodeCycle()
        self.dgraph = DependencyGraph.DependencyGraph(
            self.tnc.comps,
            self.tnc.deps,
            is_strict=False,
            verbosity=0)
    def test_num_edges(self):
        self.assertTrue(self.dgraph.num_edges() == 2)
    def test_num_nodes(self):
        self.assertTrue(self.dgraph.num_nodes() == 3)

class ThreeNodeCycleStrict(unittest.TestCase):
    def setUp(self):
        self.tnc = ThreeNodeCycle()
    def test_cycle_exception(self):
        self.assertRaises(DependencyGraph.DependencyCycleException,
                          DependencyGraph.DependencyGraph,
                          self.tnc.comps,
                          self.tnc.deps,
                          is_strict=True,
                          verbosity=0)
        
class ThreeNodesNoEdges(unittest.TestCase):
    def setUp(self):
        tnc = ThreeNodeCycle()
        self.dgraph = DependencyGraph.DependencyGraph(
            tnc.comps,
            [],
            verbosity=0)
    def test_num_edges(self):
        self.assertTrue(self.dgraph.num_edges() == 0)
    def test_num_nodes(self):
        self.assertTrue(self.dgraph.num_nodes() == 3)
        
class FourNodeDiamond(unittest.TestCase):
    def setUp(self):
        self.comps = {
            'a': {DependencyGraph.START_KEY: timedelta(minutes=1),
                      DependencyGraph.STOP_KEY: timedelta(minutes=1)},
            'b': {DependencyGraph.START_KEY: timedelta(minutes=2),
                      DependencyGraph.STOP_KEY: timedelta(minutes=2)},
            'c': {DependencyGraph.START_KEY: timedelta(minutes=4),
                      DependencyGraph.STOP_KEY: timedelta(minutes=4)},
            'd': {DependencyGraph.START_KEY: timedelta(minutes=4),
                      DependencyGraph.STOP_KEY: timedelta(minutes=8)},
        }
        self.deps = [
            {DependencyGraph.COMPONENT_KEY: 'a',
                 DependencyGraph.REQUIREMENT_KEY: 'b'},
            {DependencyGraph.COMPONENT_KEY: 'a',
                 DependencyGraph.REQUIREMENT_KEY: 'c'},
            {DependencyGraph.COMPONENT_KEY: 'b',
                 DependencyGraph.REQUIREMENT_KEY: 'd'},
            {DependencyGraph.COMPONENT_KEY: 'c',
                 DependencyGraph.REQUIREMENT_KEY: 'd'},
        ]
        self.dgraph = DependencyGraph.DependencyGraph(
            self.comps,
            self.deps,
            verbosity=0)
    def test_num_edges(self):
        self.assertTrue(self.dgraph.num_edges() == 4)
    def test_num_nodes(self):
        self.assertTrue(self.dgraph.num_nodes() == 4)

class SixNodeGraphWithCyclesNonStrict(unittest.TestCase):
    def setUp(self):
        comps = {
            'a': {DependencyGraph.START_KEY: timedelta(minutes=1),
                      DependencyGraph.STOP_KEY: timedelta(minutes=1)},
            'b': {DependencyGraph.START_KEY: timedelta(minutes=2),
                      DependencyGraph.STOP_KEY: timedelta(minutes=2)},
            'c': {DependencyGraph.START_KEY: timedelta(minutes=4),
                      DependencyGraph.STOP_KEY: timedelta(minutes=4)},
            'x': {DependencyGraph.START_KEY: timedelta(minutes=8),
                      DependencyGraph.STOP_KEY: timedelta(minutes=8)},
            'y': {DependencyGraph.START_KEY: timedelta(minutes=16),
                      DependencyGraph.STOP_KEY: timedelta(minutes=16)},
            'z': {DependencyGraph.START_KEY: timedelta(minutes=32),
                      DependencyGraph.STOP_KEY: timedelta(minutes=32)}
            }
        deps = [
            {DependencyGraph.COMPONENT_KEY: 'a',
                 DependencyGraph.REQUIREMENT_KEY: 'x'},
            {DependencyGraph.COMPONENT_KEY: 'a',
                 DependencyGraph.REQUIREMENT_KEY: 'y'},
            {DependencyGraph.COMPONENT_KEY: 'b',
                 DependencyGraph.REQUIREMENT_KEY: 'x'},
            {DependencyGraph.COMPONENT_KEY: 'c',
                 DependencyGraph.REQUIREMENT_KEY: 'c'},
            {DependencyGraph.COMPONENT_KEY: 'x',
                 DependencyGraph.REQUIREMENT_KEY: 'y'},
            {DependencyGraph.COMPONENT_KEY: 'x',
                 DependencyGraph.REQUIREMENT_KEY: 'z'},
            {DependencyGraph.COMPONENT_KEY: 'y',
                 DependencyGraph.REQUIREMENT_KEY: 'z'},
            {DependencyGraph.COMPONENT_KEY: 'z',
                 DependencyGraph.REQUIREMENT_KEY: 'b'},
            {DependencyGraph.COMPONENT_KEY: 'z',
                 DependencyGraph.REQUIREMENT_KEY: 'y'},
        ]
        self.dgraph = DependencyGraph.DependencyGraph(
            comps,
            deps,
            is_strict=False,
            verbosity=0)
    def test_num_edges(self):
        self.assertTrue(self.dgraph.num_edges() == 6)
    def test_num_nodes(self):
        self.assertTrue(self.dgraph.num_nodes() == 6)
        
if __name__=='__main__':
    unittest.main()
