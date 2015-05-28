# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
import os
from sys import stderr

from redis import Redis
from future import standard_library
from IPython.parallel.error import TimeoutError
with standard_library.hooks():
    from configparser import ConfigParser

from moi.context import Context  # noqa


REDIS_KEY_TIMEOUT = 84600 * 14  # two weeks


# parse the config bits
_config = ConfigParser()
with open(os.environ['MOI_CONFIG_FP']) as conf:
    _config.readfp(conf)


# establish a connection to the redis server
r_client = Redis(host=_config.get('redis', 'host'),
                 port=_config.getint('redis', 'port'),
                 password=_config.get('redis', 'password'),
                 db=_config.get('redis', 'db'))


# setup contexts
ctxs = {}
failed = []
for name in _config.get('ipython', 'context').split(','):
    try:
        ctxs[name] = Context(name)
    except (TimeoutError, IOError, ValueError):
        failed.append(name)

if failed:
    stderr.write('Unable to connect to ipcluster(s): %s\n' % ', '.join(failed))

ctx_default = _config.get('ipython', 'default')


__version__ = '0.1.0-dev'
__all__ = ['r_client', 'ctxs', 'ctx_default', 'REDIS_KEY_TIMEOUT']
