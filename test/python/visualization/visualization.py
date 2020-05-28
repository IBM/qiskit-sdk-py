# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# pylint: disable=missing-docstring

"""Tests class with methods for comparing the outputs of visualization tools with expected ones.
Useful for refactoring purposes."""

import os
import unittest
import matplotlib

from qiskit.test import QiskitTestCase

matplotlib.use('ps')


def path_to_diagram_reference(filename):
    return os.path.join(_this_directory(), 'references', filename)


def _this_directory():
    return os.path.dirname(os.path.abspath(__file__))


class QiskitVisualizationTestCase(QiskitTestCase):
    """Visual accuracy of visualization tools outputs tests."""

    def assertFilesAreEqual(self, current, expected):
        """Checks if both file are the same."""
        self.assertTrue(os.path.exists(current))
        self.assertTrue(os.path.exists(expected))
        with open(current, "r", encoding='cp437') as cur, \
                open(expected, "r", encoding='cp437') as exp:
            self.assertEqual(cur.read(), exp.read())

    def assertImagesAreEqual(self, current, expected, diff_tolerance=0.001):
        """Checks if both images are similar enough to be considered equal.
        Similarity is controlled by the ```diff_tolerance``` argument."""
        from PIL import Image, ImageChops

        if isinstance(current, str):
            current = Image.open(current)
            print(f'current {current.size[0]} by {current.size[1]}
                  {_get_black_pixels(current)}')
        if isinstance(expected, str):
            expected = Image.open(expected)
            print(f'expected {expected.size[0]} by {expected.size[1]}
                  {_get_black_pixels(expected)}')
        diff = ImageChops.difference(expected, current)
        black_pixels = _get_black_pixels(diff)
        total_pixels = diff.size[0] * diff.size[1]
        similarity_ratio = black_pixels / total_pixels
        print('similarity ratio')
        if 1 - similarity_ratio > diff_tolerance:
            print(similarity_ratio)
        self.assertTrue(
            1 - similarity_ratio < diff_tolerance,
            'The images are different by more than a {}%'
            .format(diff_tolerance * 100))


def _get_black_pixels(image):
    black_and_white_version = image.convert('1')
    black_pixels = black_and_white_version.histogram()[0]
    return black_pixels


if __name__ == '__main__':
    unittest.main(verbosity=2)
