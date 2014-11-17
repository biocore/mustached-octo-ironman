r"""Redis group communication"""

# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from uuid import uuid4

import toredis
from redis import ResponseError
from tornado.escape import json_decode, json_encode

from moi import r_client

_children_key = lambda x: x + ':children'
_pubsub_key = lambda x: x + ':pubsub'


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

        self.group = group
        self.group_children = _children_key(group)
        self.group_pubsub = _pubsub_key(group)

        if forwarder is None:
            self.forwarder = lambda x: None
        else:
            self.forwarder = forwarder

        self.listen_for_updates()
        for node in self._traverse(self.group):
            self.listen_to_node(node['id'])

    def _traverse(self, id_):
        """Traverse groups and yield info dicts for jobs"""

        nodes = r_client.smembers(_children_key(id_))
        while nodes:
            current_id = nodes.pop()

            details = self._decode(r_client.get(current_id))
            if details['type'] == 'group':
                children = r_client.smembers(_children_key(details['id']))
                if children is not None:
                    nodes.update(children)

            yield details

    def __del__(self):
        self.close()

    def close(self):
        """Unsubscribe the group and all jobs being listened too"""
        for channel in self._listening_to:
            self.toredis.unsubscribe(channel)
        self.toredis.unsubscribe(self.group_pubsub)

    def _decode(self, data):
        try:
            return json_decode(data)
        except (ValueError, TypeError):
            raise ValueError("Unable to decode data!")

    @property
    def jobs(self):
        """Get the known job IDs"""
        return self._listening_to.values()

    def listen_for_updates(self):
        """Attach a callback on the group pubsub"""
        self.toredis.subscribe(self.group_pubsub, callback=self.callback)

    def listen_to_node(self, id_):
        """Attach a callback on the job pubsub if it exists"""
        if r_client.get(id_) is None:
            return
        else:
            self.toredis.subscribe(_pubsub_key(id_), callback=self.callback)
            self._listening_to[_pubsub_key(id_)] = id_
            return id_

    def unlisten_to_node(self, id_):
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
        id_pubsub = _pubsub_key(id_)

        if id_pubsub in self._listening_to:
            del self._listening_to[id_pubsub]
            self.toredis.unsubscribe(id_pubsub)

            parent = json_decode(r_client.get(id_))['parent']
            if parent is not None:
                r_client.srem(_children_key(parent), id_)

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

        for verb, args in payload.items():
            action_f(verb, args)

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
            response = ({'add': i} for i in self._action_add(args))
        elif verb == 'remove':
            response = ({'remove': i} for i in self._action_remove(args))
        elif verb == 'get':
            response = ({'get': i} for i in self._action_get(args))
        else:
            raise ValueError("Unknown action: %s" % verb)

        self.forwarder(response)

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
            response = ({'update': i} for i in self._action_get(args))
        else:
            raise ValueError("Unknown job action: %s" % verb)

        self.forwarder(response)

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
        return self._action_get((self.listen_to_node(id_) for id_ in ids))

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
        return self._action_get((self.unlisten_to_node(id_) for id_ in ids))

    def _action_get(self, ids):
        """Get the details for ids

        Parameters
        ----------
        ids : {list, set, tuple, generator} of str
            The IDs to get

        Notes
        -----
        If ids is empty, then all IDs are returned.

        Returns
        -------
        list of dict
            The details of the jobs
        """
        if not ids:
            ids = self.jobs
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


def create_info(name, info_type, url=None, parent=None, id=None, store=False):
    """Return a group object"""
    id = str(uuid4()) if id is None else id
    pubsub = _pubsub_key(id)

    info = {'id': id,
            'type': info_type,
            'pubsub': pubsub,
            'url': url,
            'parent': parent,
            'name': name,
            'status': 'Queued' if info_type == 'job' else None,
            'date_start': None,
            'date_end': None,
            'result': None}

    if store:
        r_client.set(id, json_encode(info))

        if parent is not None:
            r_client.sadd(_children_key(parent), id)

    return info


def get_user_from_id(id):
    """Gets a user from an ID"""
    return r_client.hget('user-id-map', id)


def get_id_from_user(user):
    """Get an ID from a user, creates if necessary"""
    id = r_client.hget('user-id-map', user)
    if id is None:
        id = str(uuid4())
        r_client.hset('user-id-map', user, id)
        r_client.hset('user-id-map', id, user)
    return id
