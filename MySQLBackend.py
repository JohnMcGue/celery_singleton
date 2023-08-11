from celery_singleton import BaseBackend
from ssm_cache import SSMParameterGroup

class MySQLBackend(BaseBackend):
    def __init__(self, *args, **kwargs):
        try:
            self.session = kwargs['session']
        except KeyError:
            raise ValueError("Required keyword argument 'session' is missing.")

    def lock(self, lock, task_id, expiry=None):
        return not not self.redis.set(lock, task_id, nx=True, ex=expiry)

    def unlock(self, lock):
        self.redis.delete(lock)

    def get(self, lock):
        return self.redis.get(lock)

    def clear(self, key_prefix):
        cursor = 0
        while True:
            cursor, keys = self.redis.scan(cursor=cursor, match=key_prefix + "*")
            for k in keys:
                self.redis.delete(k)
            if cursor == 0:
                break