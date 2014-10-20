import json
from uuid import uuid4
from functools import partial

from moi import r_client, ctx, REDIS_KEY_TIMEOUT


def _status_change(id, redis, new_status):
    """Update the status of a job

    The status associated with the id is updated, an update command is
    issued to the job's pubsub, and and the old status is returned.

    Parameters
    ----------
    id : str
        The job ID
    redis : Redis
        A Redis client
    new_status : str
        The status change

    Returns
    -------
    str
        The old status
    """
    job_info = json.loads(redis.get(id))
    old_status = job_info['status']
    job_info['status'] = new_status

    with redis.pipeline() as pipe:
        pipe.set(id, json.dumps(job_info), ex=REDIS_KEY_TIMEOUT)
        pipe.publish(job_info['pubsub'], json.dumps({"update": [id]}))
        pipe.execute()

    return old_status


def _redis_wrap(job_info, func, *args, **kwargs):
    """Wrap something to compute

    The function that will have available, via kwargs['update_status'], a
    method to modify the job status. This method can be used within the
    executing function by:

        old_status = kwargs['update_status']('my new status')

    Parameters
    ----------
    job_info : dict
       Redis job details
    func : function
        A function to execute. This function must accept ``**kwargs``, and will
        have ``update_status`` available as a key.
    """
    def _deposit_payload(to_deposit):
        """Store job info, and publish an update

        Parameters
        ----------
        job_info : dict
            The job info

        """
        pubsub = to_deposit['pubsub']
        id = to_deposit['id']
        job_data_serialized = json.dumps(to_deposit)
        with r_client.pipeline() as pipe:
            pipe.set(id, job_data_serialized, ex=REDIS_KEY_TIMEOUT)
            pipe.publish(pubsub, json.dumps({"update": [id]}))
            pipe.execute()

    status_changer = partial(_status_change, job_info['id'], r_client)
    kwargs['update_status'] = status_changer

    job_info['status'] = 'Running'
    _deposit_payload(job_info)
    try:
        job_info['result'] = func(*args, **kwargs)
        job_info['status'] = 'Success'
    except Exception:
        import sys
        import traceback
        job_info['result'] = repr(traceback.format_exception(*sys.exc_info()))
        job_info['status'] = 'Failed'
    finally:
        _deposit_payload(job_info)


def submit(group, name, handler, func, *args, **kwargs):
    """Submit a function to a cluster

    Parameters
    ----------
    group : str
        A group that the job is a part of
    name : str
        The name of the job
    handler : url
        The handler that can take the results (e.g., /beta_diversity/)
    func : function
        The function to execute. Any returns from this function will be
        serialized and deposited into Redis using the uuid for a key.
    args : tuple or None
        Any args for ``f``
    kwargs : dict or None
        Any kwargs for ``f``

    Returns
    -------
    str
        The job ID
    """
    id = str(uuid4())

    group_jobs_key = group + ':jobs'
    group_pubsub_key = group + ':pubsub'
    job_pubsub_key = id + ':pubsub'

    job_info = {'id': id,
                'pubsub': job_pubsub_key,
                'handler': handler,
                'group': group,
                'name': name,
                'status': 'Queued',
                'result': None}

    with r_client.pipeline() as pipe:
        pipe.set(id, json.dumps(job_info))
        pipe.sadd(group_jobs_key, id)
        pipe.publish(group_pubsub_key, json.dumps({'add': [id]}))
        pipe.execute()

    ctx.submit_async(_redis_wrap, job_info, func, *args, **kwargs)
    return id


def submit_nouser(func, *args, **kwargs):
    """Submit a function to a cluster without an associated user

    Parameters
    ----------
    func : function
        The function to execute. Any returns from this function will be
        serialized and deposited into Redis using the uuid for a key.
    args : tuple or None
        Any args for ``f``
    kwargs : dict or None
        Any kwargs for ``f``

    Returns
    -------
    str
        The job ID
    """
    return submit("no-user", "unnamed", None, func, *args, **kwargs)
