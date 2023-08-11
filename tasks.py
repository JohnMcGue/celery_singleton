from celery import Celery
import os
import time
from celery_singleton import Singleton
from ssm_cache import SSMParameterGroup

environment = os.environ.get("environment")
app = Celery('tasks', broker=os.environ['CELERY_BROKER_URL'])
celery_group = SSMParameterGroup(max_age=60, base_path=f"/redis/{environment}")

singleton_backend_url = "redis://{db_username}:{db_password}@{db_uri}:6379".format(
    db_username=celery_group.parameter("/celery-cache-username").value,
    db_password=celery_group.parameter("/celery-cache-password").value,
    db_uri=celery_group.parameter("/url").value,
)

app = Celery('tasks', broker=os.environ['CELERY_BROKER_URL'])
app.conf.update(
    result_backend=os.environ['CELERY_RESULT_BACKEND'],
    singleton_backend_url=singleton_backend_url,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Europe/Oslo',
    enable_utc=True,
    task_acks_late = True,
    result_extended = True,
    worker_prefetch_multiplier = 1,
    task_routes={
        'post_data_to_db': {'queue': 'fake_post_data'}
    },
    singleton_lock_expiry=7200#two hours
)

class TestException(Exception):
    pass 

@app.task(base=Singleton,unique_on=['mbl_number', 'initiator'],name="get_tracking_data_bol", autoretry_for=(TestException,),
             retry_kwargs={'max_retries': 1, 'countdown':10}, bind=True)
def oolu_consumer(self, mbl_number=None, initiator=None, retry=False, source=None):
    print('in the task {}'.format(mbl_number))
    print(source)
    time.sleep(5)
    if retry:
        raise TestException()
    return mbl_number

@app.task(
    name="post_data_to_db",
    autoretry_for=(TestException,),
    max_retries=5,
    retry_backoff=5,
    bind=True,
)
def post_data_to_db_consumer(self, res, initiator=None):
    print(f"in post data: {res}")
    time.sleep(5)
    return res

@app.task(
    name="waiter_task",
    autoretry_for=(TestException,),
    max_retries=5,
    retry_backoff=5,
    bind=True,
)
def waiter_task(self, sleep_time):
    print(f"waiting: {sleep_time}")
    time.sleep(sleep_time)
    print("done waiting")
    return sleep_time