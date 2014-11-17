# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from IPython.parallel import Client


class Context(object):
    def __init__(self, profile):
        self.client = Client(profile=profile)
        self.bv = self.client.load_balanced_view()
