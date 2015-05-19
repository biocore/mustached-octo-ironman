# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
import os
from uuid import uuid4

from redis import Redis
from future import standard_library
with standard_library.hooks():
    from configparser import ConfigParser

from moi.context import Context  # noqa


REDIS_KEY_TIMEOUT = 84600 * 14  # two weeks


# parse the config bits
if 'MOI_CONFIG_FP' not in os.environ:
    raise IOError('$MOI_CONFIG_FP is not set')

_config = ConfigParser()
with open(os.environ['MOI_CONFIG_FP']) as conf:
    _config.readfp(conf)


# establish a connection to the redis server
r_client = Redis(host=_config.get('redis', 'host'),
                 port=_config.getint('redis', 'port'),
                 password=_config.get('redis', 'password'),
                 db=_config.get('redis', 'db'))

# make sure we can connect, let the error propogate so it can be caught
# or observed upstrean
key = 'MOI_INIT_TEST_%s' % str(uuid4())
r_client.set(key, 42)
r_client.delete(key)

# setup contexts
contexts = _config.get('ipython', 'context')
ctxs = {name: Context(name) for name in contexts.split(',')}
ctx_default = _config.get('ipython', 'default')

__version__ = '0.1.0-dev'
__all__ = ['r_client', 'ctxs', 'ctx_default', 'REDIS_KEY_TIMEOUT']
