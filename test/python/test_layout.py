# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.
# pylint: disable=invalid-name
""" Tests the layout object"""

import copy
import unittest

from qiskit import QuantumRegister
from qiskit.mapper.layout import Layout
from qiskit.mapper.exceptions import LayoutError
from qiskit.test import QiskitTestCase


class LayoutTest(QiskitTestCase):
    """Test the methods in the layout object."""

    def setUp(self):
        self.qr = QuantumRegister(3, 'qr')

    def test_default_layout(self):
        """Static method generate_trivial_layout creates a Layout"""
        qr0 = QuantumRegister(3, 'q0')
        qr1 = QuantumRegister(2, 'q1')
        layout = Layout.generate_trivial_layout(qr0, qr1)

        self.assertEqual(layout[(qr0, 0)], 0)
        self.assertEqual(layout[(qr0, 1)], 1)
        self.assertEqual(layout[(qr0, 2)], 2)
        self.assertEqual(layout[(qr1, 0)], 3)
        self.assertEqual(layout[(qr1, 1)], 4)

    def test_layout_from_dict(self):
        """Constructor from a dict"""
        layout = Layout({(self.qr, 0): 0,
                         (self.qr, 1): 1,
                         (self.qr, 2): 2})

        self.assertEqual(layout[(self.qr, 0)], 0)
        self.assertEqual(layout[(self.qr, 1)], 1)
        self.assertEqual(layout[(self.qr, 2)], 2)
        self.assertEqual(layout[0], (self.qr, 0))
        self.assertEqual(layout[1], (self.qr, 1))
        self.assertEqual(layout[2], (self.qr, 2))

    def test_layout_from_list(self):
        """Constructor from a list"""
        layout = Layout([(QuantumRegister(2, 'q0'), 0),
                         (QuantumRegister(2, 'q1'), 0),
                         None,
                         (QuantumRegister(2, 'q1'), 1),
                         (QuantumRegister(2, 'q0'), 1)])

        self.assertEqual(layout[(QuantumRegister(2, 'q0'), 0)], 0)
        self.assertEqual(layout[(QuantumRegister(2, 'q1'), 0)], 1)
        with self.assertRaises(KeyError):
            _ = layout[None]
        self.assertEqual(layout[(QuantumRegister(2, 'q1'), 1)], 3)
        self.assertEqual(layout[(QuantumRegister(2, 'q0'), 1)], 4)

        self.assertEqual(layout[0], (QuantumRegister(2, 'q0'), 0))
        self.assertEqual(layout[1], (QuantumRegister(2, 'q1'), 0))
        self.assertEqual(layout[2], None)
        self.assertEqual(layout[3], (QuantumRegister(2, 'q1'), 1))
        self.assertEqual(layout[4], (QuantumRegister(2, 'q0'), 1))

    def test_layout_set(self):
        """Setter"""
        layout = Layout()
        layout[(self.qr, 0)] = 0
        self.assertEqual(layout[(self.qr, 0)], 0)
        self.assertEqual(layout[0], (self.qr, 0))

    def test_layout_avoid_dangling_physical(self):
        """ No dangling pointers for physical qubits."""
        layout = Layout({(self.qr, 0): 0})
        self.assertEqual(layout[0], (self.qr, 0))
        layout[(self.qr, 0)] = 1
        with self.assertRaises(KeyError):
            _ = layout[0]

    def test_layout_avoid_dangling_virtual(self):
        """ No dangling pointers for virtual qubits."""
        layout = Layout({(self.qr, 0): 0})
        self.assertEqual(layout[0], (self.qr, 0))
        layout[0] = (self.qr, 1)
        with self.assertRaises(KeyError):
            print(layout[(self.qr, 0)])

    def test_layout_len(self):
        """Length of the layout is the amount of physical bits"""
        layout = Layout()
        self.assertEqual(len(layout), 0)
        layout.add((self.qr, 2))
        self.assertEqual(len(layout), 1)
        layout.add((self.qr, 1), 3)
        self.assertEqual(len(layout), 2)

    def test_layout_len_with_idle(self):
        """Length of the layout is the amount of physical bits"""
        layout = Layout()
        self.assertEqual(len(layout), 0)
        layout.add((self.qr, 2))
        self.assertEqual(len(layout), 1)
        layout.add((self.qr, 1), 3)
        self.assertEqual(len(layout), 2)

    def test_layout_idle_physical_bits(self):
        """Get physical_bits that are not mapped"""
        layout = Layout()
        layout.add((self.qr, 1), 2)
        layout.add(None, 4)
        layout.add(None, 6)
        self.assertEqual(layout.idle_physical_bits(), [4, 6])

    def test_layout_get_bits(self):
        """Get the map from the (qu)bits view"""
        layout_dict = {(self.qr, 0): 0,
                       (self.qr, 1): 1,
                       (self.qr, 2): 2}
        layout = Layout(layout_dict)
        self.assertDictEqual(layout_dict, layout.get_virtual_bits())

    def test_layout_get_physical_bits(self):
        """Get the map from the physical bits view"""
        layout = Layout({(self.qr, 0): 0, (self.qr, 1): 1, (self.qr, 2): 2})
        self.assertDictEqual(layout.get_physical_bits(), {0: (self.qr, 0),
                                                          1: (self.qr, 1),
                                                          2: (self.qr, 2)})

    def test_layout_add(self):
        """add() method"""
        layout = Layout()
        layout[(self.qr, 0)] = 0
        layout.add((self.qr, 1))

        self.assertEqual(layout[(self.qr, 1)], 1)
        self.assertEqual(layout[1], (self.qr, 1))

    def test_layout_add_register(self):
        """add_register() method"""
        layout = Layout()
        layout.add_register(QuantumRegister(2, 'q0'))
        layout.add_register(QuantumRegister(1, 'q1'))

        self.assertEqual(layout[(QuantumRegister(2, 'q0'), 0)], 0)
        self.assertEqual(layout[(QuantumRegister(2, 'q0'), 1)], 1)
        self.assertEqual(layout[(QuantumRegister(1, 'q1'), 0)], 2)

    def test_physical_keyerror(self):
        """When asking for an unexistant physical qubit, KeyError"""
        layout = Layout()
        layout[(self.qr, 0)] = 1

        with self.assertRaises(KeyError):
            _ = layout[0]

    def test_virtual_keyerror(self):
        """When asking for an unexistant virtual qubit, KeyError"""
        layout = Layout()
        layout[(self.qr, 0)] = 1

        with self.assertRaises(KeyError):
            _ = layout[(self.qr, 1)]

    def test_layout_swap(self):
        """swap() method"""
        layout = Layout()
        layout.add((self.qr, 0))
        layout.add((self.qr, 1))
        layout.swap(0, 1)
        self.assertDictEqual(layout.get_virtual_bits(), {(self.qr, 0): 1, (self.qr, 1): 0})

    def test_layout_swap_error(self):
        """swap() method error"""
        layout = Layout()
        layout.add((self.qr, 0))
        layout.add((self.qr, 1))
        with self.assertRaises(LayoutError):
            layout.swap(0, (self.qr, 0))

    def test_layout_combine(self):
        """combine_into_edge_map() method"""
        layout = Layout()
        layout.add((self.qr, 0))
        layout.add((self.qr, 1))
        another_layout = Layout()
        another_layout.add((self.qr, 1))
        another_layout.add((self.qr, 0))

        edge_map = layout.combine_into_edge_map(another_layout)
        self.assertDictEqual(edge_map, {(self.qr, 0): (self.qr, 1), (self.qr, 1): (self.qr, 0)})

    def test_layout_combine_bigger(self):
        """combine_into_edge_map() method with another_layout is bigger"""
        layout = Layout()
        layout.add((self.qr, 0))
        layout.add((self.qr, 1))
        another_layout = Layout()
        another_layout.add((self.qr, 1))
        another_layout.add((self.qr, 0))
        another_layout.add((self.qr, 2))

        edge_map = layout.combine_into_edge_map(another_layout)
        self.assertDictEqual(edge_map, {(self.qr, 0): (self.qr, 1), (self.qr, 1): (self.qr, 0)})

    def test_set_virtual_without_physical(self):
        """When adding a virtual without care in which physical is going"""
        layout = Layout()
        layout.add((self.qr, 1), 2)
        layout.add((self.qr, 0))

        self.assertDictEqual(layout.get_virtual_bits(), {(self.qr, 0): 1, (self.qr, 1): 2})

    def test_layout_combine_smaller(self):
        """combine_into_edge_map() method with another_layout is smaller and raises an Error"""
        layout = Layout()
        layout.add((self.qr, 0))
        layout.add((self.qr, 1))
        layout.add((self.qr, 2))
        another_layout = Layout()
        another_layout.add((self.qr, 1))
        another_layout.add((self.qr, 0))

        with self.assertRaises(LayoutError):
            _ = layout.combine_into_edge_map(another_layout)

    def test_copy(self):
        """Test copy methods return equivalent layouts."""
        layout = Layout()
        layout.add((self.qr, 0))
        layout.add((self.qr, 1))

        layout_dict_copy = layout.copy()
        self.assertTrue(isinstance(layout_dict_copy, Layout))
        self.assertDictEqual(layout.get_physical_bits(), layout_dict_copy.get_physical_bits())
        self.assertDictEqual(layout.get_virtual_bits(), layout_dict_copy.get_virtual_bits())

        layout_copy_copy = copy.copy(layout)
        self.assertTrue(isinstance(layout_copy_copy, Layout))
        self.assertDictEqual(layout.get_physical_bits(), layout_dict_copy.get_physical_bits())
        self.assertDictEqual(layout.get_virtual_bits(), layout_dict_copy.get_virtual_bits())

        layout_copy_deepcopy = copy.deepcopy(layout)
        self.assertTrue(isinstance(layout_copy_deepcopy, Layout))
        self.assertDictEqual(layout.get_physical_bits(), layout_dict_copy.get_physical_bits())
        self.assertDictEqual(layout.get_virtual_bits(), layout_dict_copy.get_virtual_bits())

    def test_layout_error_str_key(self):
        """Layout does not work with strings"""
        layout = Layout()

        with self.assertRaises(LayoutError):
            layout['a_string'] = 3

        with self.assertRaises(LayoutError):
            layout[2] = 'a_string'

    def test_layout_error_when_same_type(self):
        """Layout does not work when key and value are the same type"""
        layout = Layout()

        with self.assertRaises(LayoutError):
            layout[(self.qr, 0)] = (self.qr, 1)

        with self.assertRaises(LayoutError):
            layout[0] = 1

    def test_layout_repr(self):
        """Layout repr reproduces layout"""
        qr = QuantumRegister(5, 'qr')
        layout = Layout({(qr, 0): 2,
                         (qr, 1): 4,
                         (qr, 2): 3,
                         (qr, 3): 0,
                         (qr, 4): 1,
                         })

        repr_layout = eval(layout.__repr__())  # pylint: disable=eval-used
        self.assertDictEqual(layout._p2v, repr_layout._p2v)
        self.assertDictEqual(layout._v2p, repr_layout._v2p)

    def test_layout_repr_with_holes(self):
        """A non-bijective Layout repr reproduces layout"""
        qr = QuantumRegister(5, 'qr')
        layout = Layout([(qr, 0), None, None, (qr, 1), (qr, 2), (qr, 3), (qr, 4), None])

        repr_layout = eval(layout.__repr__())  # pylint: disable=eval-used
        self.assertDictEqual(layout._p2v, repr_layout._p2v)
        self.assertDictEqual(layout._v2p, repr_layout._v2p)

    def test_layout_from_intlist(self):
        """Create a layout from a list of integers.
        virtual  physical
         q1_0  ->  4
         q2_0  ->  5
         q2_1  ->  6
         q3_0  ->  8
         q3_1  ->  9
         q3_2  ->  10
        """
        q1 = QuantumRegister(1, 'q1')
        q2 = QuantumRegister(2, 'q2')
        q3 = QuantumRegister(3, 'q3')
        intlist_layout = [4, 5, 6, 8, 9, 10]
        layout = Layout.intlist_layout(intlist_layout, q1, q2, q3)

        expected = Layout({4: (QuantumRegister(1, 'q1'), 0),
                           5: (QuantumRegister(2, 'q2'), 0),
                           6: (QuantumRegister(2, 'q2'), 1),
                           8: (QuantumRegister(3, 'q3'), 0),
                           9: (QuantumRegister(3, 'q3'), 1),
                           10: (QuantumRegister(3, 'q3'), 2)
                           })
        self.assertDictEqual(layout._p2v, expected._p2v)
        self.assertDictEqual(layout._v2p, expected._v2p)

    def test_layout_from_intlist_short(self):
        """If the intlist is longer that your quantum register, map them to None.
        virtual  physical
         q1_0  ->  4
         q2_0  ->  5
         q2_1  ->  6
         None  ->  8
         None  ->  9
         None  ->  10
        """
        q1 = QuantumRegister(1, 'q1')
        q2 = QuantumRegister(2, 'q2')

        intlist_layout = [4, 5, 6, 8, 9, 10]
        layout = Layout.intlist_layout(intlist_layout, q1, q2)

        expected = Layout({4: (QuantumRegister(1, 'q1'), 0),
                           5: (QuantumRegister(2, 'q2'), 0),
                           6: (QuantumRegister(2, 'q2'), 1),
                           8: None,
                           9: None,
                           10: None
                           })
        self.assertDictEqual(layout._p2v, expected._p2v)
        self.assertDictEqual(layout._v2p, expected._v2p)

    def test_layout_from_intlist_long(self):
        """If the intlist is shorter that your quantum register, fail.
        virtual  physical
         q1_0  ->  4
         q2_0  ->  5
         q2_1  ->  6
         q3_0  ->  8
         q3_1  ->  ?
         q3_2  ->  ?
        """
        q1 = QuantumRegister(1, 'q1')
        q2 = QuantumRegister(2, 'q2')
        q3 = QuantumRegister(3, 'q3')
        intlist_layout = [4, 5, 6, 8]

        with self.assertRaises(LayoutError):
            _ = Layout.intlist_layout(intlist_layout, q1, q2, q3)

    def test_layout_from_intlist_duplicated(self):
        """If the intlist contains duplicated ints, fail.
        virtual  physical
         q1_0  ->  4
         q2_0  ->  6 -- This is
         q2_1  ->  6 -- not allowed
        """
        q1 = QuantumRegister(1, 'q1')
        q2 = QuantumRegister(2, 'q2')
        intlist_layout = [4, 6, 6]

        with self.assertRaises(LayoutError):
            _ = Layout.intlist_layout(intlist_layout, q1, q2)


if __name__ == '__main__':
    unittest.main()
