from redis import Redis
from moi.context import Context


REDIS_KEY_TIMEOUT = 84600 * 14  # two weeks

r_client = Redis()
ctx = Context('qiita_demo')


__all__ = ['r_client', 'ctx', 'REDIS_KEY_TIMEOUT']
