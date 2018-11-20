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


class Layout(dict):
    """ Two-ways dict to represent a Layout."""

    def __init__(self, input_=None):
        dict.__init__(self)
        if isinstance(input_, dict):
            self.from_dict(input_)
        if isinstance(input_, list):
            self.from_list(input_)

    def from_dict(self, input_dict):
        for key, value in input_dict.items():
            self[key] = value

    def from_list(self, input_list):
        for key, value in enumerate(input_list):
            self[key] = value

    def __getitem__(self, item):
        if item is None:
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
        return dict.__len__(self) // 2

    def add_logical(self, logical, physical=None):
        if physical is None:
            physical = len(self)
        self[logical] = physical

    def get_logical(self):
        return {key: value for key, value in self.items() if isinstance(key, tuple)}

    def swap(self, left, right):
        temp = self[left]
        self[left] = self[right]
        self[right] = temp
