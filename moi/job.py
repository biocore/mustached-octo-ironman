# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

import sys
import traceback
import json
from functools import partial
from datetime import datetime
from subprocess import Popen, PIPE

from moi import r_client, ctxs, ctx_default, REDIS_KEY_TIMEOUT
from moi.group import create_info
from moi.context import Context


def system_call(cmd, **kwargs):
    """Call cmd and return (stdout, stderr, return_value).

    Parameters
    ----------
    cmd: str
        Can be either a string containing the command to be run, or a sequence
        of strings that are the tokens of the command.
    kwargs : dict, optional
        Ignored. Available so that this function is compatible with
        _redis_wrap.

    Notes
    -----
    This function is ported from QIIME (http://www.qiime.org), previously
    named qiime_system_call. QIIME is a GPL project, but we obtained permission
    from the authors of this function to port it to pyqi (and keep it under
    pyqi's BSD license).
    """
    proc = Popen(cmd,
                 universal_newlines=True,
                 shell=True,
                 stdout=PIPE,
                 stderr=PIPE)
    # communicate pulls all stdout/stderr from the PIPEs to
    # avoid blocking -- don't remove this line!
    stdout, stderr = proc.communicate()
    return_value = proc.returncode

    if return_value != 0:
        raise ValueError("Failed to execute: %s\nstdout: %s\nstderr: %s" %
                         (cmd, stdout, stderr))

    return stdout, stderr, return_value


def _status_change(id, new_status):
    """Update the status of a job

    The status associated with the id is updated, an update command is
    issued to the job's pubsub, and and the old status is returned.

    Parameters
    ----------
    id : str
        The job ID
    new_status : str
        The status change

    Returns
    -------
    str
        The old status
    """
    job_info = json.loads(r_client.get(id).decode('utf-8'))
    old_status = job_info['status']
    job_info['status'] = new_status
    _deposit_payload(job_info)

    return old_status


def _deposit_payload(to_deposit):
    """Store job info, and publish an update

    Parameters
    ----------
    to_deposit : dict
        The job info

    """
    pubsub = to_deposit['pubsub']
    id = to_deposit['id']

    with r_client.pipeline() as pipe:
        pipe.set(id, json.dumps(to_deposit), ex=REDIS_KEY_TIMEOUT)
        pipe.publish(pubsub, json.dumps({"update": [id]}))
        pipe.execute()


def _redis_wrap(job_info, func, *args, **kwargs):
    """Wrap something to compute

    The function that will have available, via kwargs['moi_update_status'], a
    method to modify the job status. This method can be used within the
    executing function by:

        old_status = kwargs['moi_update_status']('my new status')

    Parameters
    ----------
    job_info : dict
       Redis job details
    func : function
        A function to execute. This function must accept ``**kwargs``, and will
        have ``moi_update_status``, ``moi_context`` and ``moi_parent_id``
        available.

    Raises
    ------
    Exception
        If the function called raises, that exception is propagated.

    Returns
    -------
    Anything the function executed returns.
    """
    status_changer = partial(_status_change, job_info['id'])
    kwargs['moi_update_status'] = status_changer
    kwargs['moi_context'] = job_info['context']
    kwargs['moi_parent_id'] = job_info['parent']

    job_info['status'] = 'Running'
    job_info['date_start'] = str(datetime.now())

    _deposit_payload(job_info)

    caught = None
    try:
        result = func(*args, **kwargs)
        job_info['status'] = 'Success'
    except Exception as e:
        result = traceback.format_exception(*sys.exc_info())
        job_info['status'] = 'Failed'
        caught = e
    finally:
        job_info['result'] = result
        job_info['date_end'] = str(datetime.now())
        _deposit_payload(job_info)

    if caught is None:
        return result
    else:
        raise caught


def submit(ctx_name, *args, **kwargs):
    """Submit through a context"""
    if isinstance(ctx_name, Context):
        ctx = ctx_name
    else:
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
        serialized and deposited into Redis using the uuid for a key. This
        function should raise if the method fails.
    args : tuple or None
        Any args for ``f``
    kwargs : dict or None
        Any kwargs for ``f``

    Returns
    -------
    tuple, (str, str, AsyncResult)
        The job ID and the parent ID
    """
    parent_info = r_client.get(parent_id)
    if parent_info is None:
        parent_info = create_info('unnamed', 'group', id=parent_id)
        parent_id = parent_info['id']
        r_client.set(parent_id, json.dumps(parent_info))

    parent_pubsub_key = parent_id + ':pubsub'

    job_info = create_info(name, 'job', url=url, parent=parent_id,
                           context=ctx.name, store=True)
    job_info['status'] = 'Queued'
    job_id = job_info['id']

    with r_client.pipeline() as pipe:
        pipe.set(job_id, json.dumps(job_info))
        pipe.publish(parent_pubsub_key, json.dumps({'add': [job_id]}))
        pipe.execute()

    ar = ctx.bv.apply_async(_redis_wrap, job_info, func, *args, **kwargs)
    return job_id, parent_id, ar


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
    tuple, (str, str)
        The job ID and the parent ID
    """
    return submit(ctx_default, "no-user", "unnamed", None, func, *args,
                  **kwargs)
