# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""
A two-ways dict that represent a layout.

Layout is the relation between logical (qu)bits and physical (qu)bits.
Logical (qu)bits are tuples (eg, `('qr',2)`.
Physical (qu)bits are numbers.
"""

from qiskit import QISKitError


class Layout(dict):
    """ Two-ways dict to represent a Layout."""

    def __init__(self, input_=None):
        dict.__init__(self)
        if isinstance(input_, dict):
            self.from_dict(input_)
        if isinstance(input_, list):
            self.from_list(input_)

    def from_dict(self, input_dict):
        """
        Pullulates a Layout from a dictionary.

        Args:
            input_dict (dict): For example,
            {('qr', 0): 0, ('qr', 1): 1, ('qr', 2): 2}
        """
        for key, value in input_dict.items():
            self[key] = value

    def from_list(self, input_list):
        """
        Pullulates a Layout from a list.

        Args:
            input_list (list): For example,
            [('qr', 0), None, ('qr', 2), ('qr', 3)]
        """
        for key, value in enumerate(input_list):
            self[key] = value

    def __getitem__(self, item):
        if item is None:
            return None
        if isinstance(item,int) and item < len(self) and item not in self:
            return None
        return dict.__getitem__(self, item)

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        return max([key for key in self.keys() if isinstance(key, int)], default=-1) + 1

    def add(self, logical, physical=None):
        if physical is None:
            physical = len(self)
        self[logical] = physical

    def length(self, amount_of_wires):
        current_length = len(self)
        if amount_of_wires < current_length:
            raise LayoutError('Lenght setting cannot be smaller than the current amount of wires.')
        for new_wire in range(current_length, amount_of_wires):
            self[new_wire] = None

    def idle_wires(self):
        idle_wire_list = []
        for wire in range(len(self)):
            if self[wire] is None:
                idle_wire_list.append(wire)
        return idle_wire_list

    def get_logical(self):
        return {key: value for key, value in self.items() if isinstance(key, tuple)}

    def get_physical(self):
        return {key: value for key, value in self.items() if isinstance(key, int)}

    def swap(self, left, right):
        temp = self[left]
        self[left] = self[right]
        self[right] = temp


class LayoutError(QISKitError):
    def __init__(self, *msg):
        """Set the error message."""
        super().__init__(*msg)
        self.msg = ' '.join(msg)

    def __str__(self):
        """Return the message."""
        return repr(self.msg)
