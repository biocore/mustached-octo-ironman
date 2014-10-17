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
        pipe.publish(job_info['pubsub'], json.dumps({"update": "status"}))
        pipe.execute()

    return old_status


def _redis_wrap(redis_deets, func, *args, **kwargs):
    """Wrap something to compute

    The function that will have available, via kwargs['update_status'], a
    method to modify the job status. This method can be used within the
    executing function by:

        old_status = kwargs['update_status']('my new status')

    Parameters
    ----------
    redis_deets : dict
        Redis details, specifically:
            {'id': <str, the job ID>,
             'pubsub': <str, the pubsub key for the job>,
             'group': <str, the group the job is a part of>,
             'handler': <URL or None, the results handler>}
    func : function
        A function to execute. This function must accept ``**kwargs``, and will
        have ``update_status`` available as a key.
    """
    def _deposit_payload(job_info):
        """Store job info, and publish an update

        Parameters
        ----------
        job_info : dict
            The job info

        """
        pubsub = job_info['pubsub']
        id = job_info['id']
        job_data_serialized = json.dumps(job_info)

        with r_client.pipeline() as pipe:
            pipe.set(id, job_data_serialized, ex=REDIS_KEY_TIMEOUT)
            pipe.publish(pubsub, json.dumps({"update": None}))
            pipe.execute()

    job_info = {'id': redis_deets['id'],
                'pubsub': redis_deets['pubsub'],
                'handler': redis_deets['handler'],
                'group': redis_deets['group'],
                'status': 'Running',
                'result': None}

    status_changer = partial(_status_change, job_info['id'], r_client)
    kwargs['update_status'] = status_changer

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

    with r_client.pipeline() as pipe:
        # add the job to the group
        pipe.sadd(group_jobs_key, id)
        pipe.publish(group_pubsub_key, {'add': id})
        pipe.execute()

    redis_deets = {'pubsub': job_pubsub_key,
                   'id': id,
                   'group': group,
                   'handler': handler}

    ctx.submit_async(_redis_wrap, redis_deets, func, *args, **kwargs)
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
