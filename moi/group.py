"""Redis group communication"""

import toredis
from redis import ResponseError
from tornado.gen import coroutine, Task
from tornado.escape import json_decode

from moi import r_client


class Group(object):
    """A object-relational mapper against a Redis job group

    Parameters
    ----------
    group : str
        A group, this name subscribed to for "group" state changes.
    forwarder : function
        A function to forward on state changes to. This function must accept a
        `dict`. Any return is ignored.
    """
    def __init__(self, group, forwarder=None):
        self.toredis = toredis.Client()
        self.toredis.connect()

        self._listening_to = {}

        self.group_jobs = group + ':jobs'
        self.group_pubsub = group + ':pubsub'

        if forwarder is None:
            self.forwarder = lambda x: None
        else:
            self.forwarder = forwarder

        self.listen_for_updates()
        for job_id in r_client.smembers(self.group_jobs):
            self.listen_to_job(job_id)

    def __del__(self):
        self.close()

    @coroutine
    def close(self):
        """Unsubscribe the group and all jobs being listened too"""
        for channel in self._listening_to:
            yield Task(self.toredis.unsubscribe, channel)
        yield Task(self.toredis.unsubscribe, self.group_pubsub)

        self.toredis.disconnect()

    def _decode(self, data):
        try:
            return json_decode(data)
        except (ValueError, TypeError):
            raise ValueError("Unable to decode data!")

    def listen_for_updates(self):
        """Attach a callback on the group pubsub"""
        self.toredis.subscribe(self.group_pubsub, callback=self.callback)

    def listen_to_job(self, id_):
        """Attach a callback on the job pubsub if it exists"""
        if r_client.get(id_) is None:
            return
        else:
            self.toredis.subscribe(id_ + ':pubsub', callback=self.callback)
            self._listening_to[id_ + ':pubsub'] = id_
            return id_

    def unlisten_to_job(self, id_):
        """Stop listening to a job

        Parameters
        ----------
        id_ : str
            An ID to remove

        Returns
        --------
        str or None
            The ID removed or None if the ID was not removed
        """
        id_pubsub = id_ + ':pubsub'

        if id_pubsub in self._listening_to:
            del self._listening_to[id_pubsub]
            self.toredis.unsubscribe(id_pubsub)
            r_client.srem(self.group_jobs, id_)
            return id_
        else:
            return None

    def callback(self, msg):
        """Accept a message that was published, process and forward

        Parameters
        ----------
        msg : tuple, (str, str, str)
            The message sent over the line. The `tuple` is of the form:
            (message_type, channel, payload).

        Notes
        -----
        This method only handles messages where `message_type` is "message".

        Raises
        ------
        ValueError
            If the channel is not known.
        """
        message_type, channel, payload = msg

        if message_type != 'message':
            return

        try:
            payload = self._decode(payload)
        except ValueError:
            # unable to decode so we cannot handle the message
            return

        if channel == self.group_pubsub:
            action_f = self.action
        elif channel in self._listening_to:
            action_f = self.job_action
        else:
            raise ValueError("Callback triggered unexpectedly by %s" % channel)

        to_forward = (action_f(verb, args) for verb, args in payload.items())
        self.forwarder(to_forward)

    def action(self, verb, args):
        """Process the described action

        Parameters
        ----------
        verb : str, {'add', 'remove', 'get'}
            The specific action to perform
        args : {list, set, tuple}
            Any relevant arguments for the action.

        Raises
        ------
        TypeError
            If args is an unrecognized type
        ValueError
            If the action specified is unrecognized

        Returns
        -------
        list
            Elements dependent on the action
        """
        if not isinstance(args, (list, set, tuple)):
            raise TypeError("args is unknown type: %s" % type(args))

        if verb == 'add':
            response = {'add': self._action_add(args)}
        elif verb == 'remove':
            response = {'remove': self._action_remove(args)}
        elif verb == 'get':
            response = {'get': self._action_get(args)}
        else:
            raise ValueError("Unknown action: %s" % verb)

        return response

    def job_action(self, verb, args):
        """Process the described action

        verb : str, {'update'}
            The specific action to perform
        args : {list, set, tuple}
            Any relevant arguments for the action.

        Raises
        ------
        TypeError
            If args is an unrecognized type
        ValueError
            If the action specified is unrecognized

        Returns
        -------
        list
            Elements dependent on the action
        """
        if not isinstance(args, (list, set, tuple)):
            raise TypeError("args is unknown type: %s" % type(args))

        if verb == 'update':
            response = {'update': self._action_get(args)}
        else:
            raise ValueError("Unknown job action: %s" % verb)

        return response

    def _action_add(self, ids):
        """Add IDs to the group

        Parameters
        ----------
        ids : {list, set, tuple, generator} of str
            The IDs to add

        Returns
        -------
        list of dict
            The details of the added jobs
        """
        return self._action_get((self.listen_to_job(id_) for id_ in ids))

    def _action_remove(self, ids):
        """Remove IDs from the group

        Parameters
        ----------
        ids : {list, set, tuple, generator} of str
            The IDs to remove

        Returns
        -------
        list of dict
            The details of the removed jobs
        """
        return self._action_get((self.unlisten_to_job(id_) for id_ in ids))

    def _action_get(self, ids):
        """Get the details for ids

        Parameters
        ----------
        ids : {list, set, tuple, generator} of str
            The IDs to get

        Returns
        -------
        list of dict
            The details of the jobs
        """
        result = []
        for id_ in ids:
            if id_ is None:
                continue

            try:
                payload = r_client.get(id_)
            except ResponseError:
                # wrong key type
                continue

            try:
                payload = self._decode(payload)
            except ValueError:
                # unable to decode or data doesn't exist in redis
                continue
            else:
                result.append(payload)
        return result
