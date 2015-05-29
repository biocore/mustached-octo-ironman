# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from os.path import exists, split
from unittest import TestCase, main

from moi import moi_js, moi_list_js


class InitTests(TestCase):
    def test_moi_js(self):
        self.assertTrue(exists(moi_js()))
        self.assertEqual(split(moi_js())[1], 'moi.js')

    def test_moi_list_js(self):
        self.assertTrue(exists(moi_list_js()))
        self.assertEqual(split(moi_list_js())[1], 'moi_list.js')


if __name__ == '__main__':
    main()
