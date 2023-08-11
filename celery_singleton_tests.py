from celery import Celery,signature
import os
from tasks import *
from ssm_cache import SSMParameterGroup

environment = os.environ.get("environment")
app = Celery('tasks', broker=os.environ['CELERY_BROKER_URL'])
celery_group = SSMParameterGroup(max_age=60, base_path=f"/redis/{environment}")

singleton_backend_url = "redis://{db_username}:{db_password}@{db_uri}:6379".format(
    db_username=celery_group.parameter("/celery-cache-username").value,
    db_password=celery_group.parameter("/celery-cache-password").value,
    db_uri=celery_group.parameter("/url").value,
)

app.conf.update(
    result_backend=os.environ['CELERY_RESULT_BACKEND'],
    singleton_backend_url=singleton_backend_url,
    task_serializer='json',
    result_extended = True,
    result_serializer='json',
    task_acks_late = True,
    accept_content=['json'],
    timezone='Europe/Oslo',
    enable_utc=True,
    task_routes={
        'get_tracking_data_bol': {'queue': 'fake_scraper'},
        'post_data_to_db': {'queue': 'fake_post_data'},
        "waiter_task": {'queue': 'waiter_queue'}
    },
    singleton_lock_expiry=3
)

@app.task(name="get_tracking_data_bol", autoretry_for=(TestException,),
             retry_kwargs={'max_retries': 1, 'countdown':10}, bind=True)
def oolu_consumer(self, mbl_number=None, initiator=None, retry=False):
    print('in the task {}'.format(mbl_number))
    time.sleep(5)
    if retry:
        raise TestException()
    return mbl_number

### Lock expiry applies to items on the queue!
def test_task_on_queue_is_duplicated():
    #queue up a task which will hold the worker for 30 seconds (worker only pulls 1 task at a time)
    chain = signature("waiter_task", args=[30])
    chain.apply_async()
    mbl = "TEST1234"
    initiator = "TEST"
    #queue up a tracking task. does not get processed, because of waiter task. sits on queue
    chain = signature("get_tracking_data_bol", args=[mbl], kwargs={"initiator": initiator})
    chain.apply_async()
    # wait for lock to expire (10 seconds)
    #time.sleep(11)
    #try to queue up another task - does it work?
    chain = signature("get_tracking_data_bol", args=[mbl], kwargs={"initiator": initiator})
    chain.apply_async()

### default singleton behavior prevents queuing of retries!!! must set unique on args. unique on args are required, which is an issue for keyword args
def test_retries_are_requeued():
    chain = signature("get_tracking_data_bol", args=[mbl], kwargs={"initiator": initiator, "retry": True})
    chain.apply_async()

def test_killed_worker():
    chain = signature("get_tracking_data_bol", args=[mbl], kwargs={"initiator": initiator, "source":"chain"})
    chain.apply_async()

if __name__ == '__main__':
    #result = add.delay(5, 4)
    #print(f'Task result: {result.get()}')
    #result = oolu_consumer.delay(5, 4)
    #print(f'Task result: {result.get()}')
    #clear_locks(app)
    mbl = "TEST1234"
    initiator = "TEST"
    #test_task_on_queue_is_duplicated()
    # oolu_consumer.apply_async(args=[mbl], kwargs={"initiator": initiator})
    # oolu_consumer.apply_async(args=[mbl], kwargs={"initiator": initiator})
    # test_killed_worker()
    # test_killed_worker()
    chain = signature("get_tracking_data_bol", args=[mbl], kwargs={"initiator": initiator})
    chain |= signature(
        "post_data_to_db",
        kwargs={"initiator": initiator},
    )
    chain.apply_async()
    chain = signature("get_tracking_data_bol", args=[mbl], kwargs={"initiator": initiator})
    chain |= signature(
        "post_data_to_db",
        kwargs={"initiator": initiator},
    )
    chain.apply_async()
    # chain = signature("get_tracking_data_bol", args=[mbl], kwargs={"initiator": initiator})
    # chain |= signature(
    #     "post_data_to_db",
    #     kwargs={"initiator": initiator},
    # )
    # chain.apply_async()
