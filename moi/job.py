import json
from functools import partial
from datetime import datetime

from moi import r_client, ctxs, ctx_default, REDIS_KEY_TIMEOUT
from moi.group import create_info


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
    kwargs['moi_context'] = ctxs

    job_info['status'] = 'Running'
    job_info['date_start'] = str(datetime.now())

    _deposit_payload(job_info)
    try:
        job_info['result'] = func(*args, **kwargs)
        job_info['status'] = 'Success'
    except Exception:
        import sys
        import traceback
        job_info['result'] = traceback.format_exception(*sys.exc_info())
        job_info['status'] = 'Failed'
    finally:
        job_info['date_end'] = str(datetime.now())
        _deposit_payload(job_info)


def submit(ctx_name, *args, **kwargs):
    """Submit through a context"""
    ctx = ctxs.get(ctx_name, ctx_default)
    return _submit(ctx, *args, **kwargs)


def _submit(ctx, parent_id, name, url, func, *args, **kwargs):
    """Submit a function to a cluster

    Parameters
    ----------
    parent_id : str
        The ID of the group that the job is a part of.
    name : str
        The name of the job
    url : str
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
    tuple, (str, str)
        The job ID and the parent ID
    """
    parent_info = r_client.get(parent_id)
    if parent_info is None:
        parent_info = create_info('unnamed', 'group', id=parent_id)
        parent_id = parent_info['id']
        r_client.set(parent_id, json.dumps(parent_info))

    parent_pubsub_key = parent_id + ':pubsub'

    job_info = create_info(name, 'job', url=url, parent=parent_id, store=True)
    job_info['status'] = 'Queued'
    job_id = job_info['id']

    with r_client.pipeline() as pipe:
        pipe.set(job_id, json.dumps(job_info))
        pipe.publish(parent_pubsub_key, json.dumps({'add': [job_id]}))
        pipe.execute()

    ctx.submit_async(_redis_wrap, job_info, func, *args, **kwargs)
    return job_id, parent_id


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
    return submit(ctx_default, "no-user", "unnamed", None, func, *args,
                  **kwargs)
