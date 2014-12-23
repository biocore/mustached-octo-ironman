r"""Pub-sub communication"""

# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from tornado.ioloop import PeriodicCallback

from collections import defaultdict


class PubSub(object):
    def __init__(self, r_client, tornado_ioloop):
        self.channel_listeners = defaultdict(list)
        self._pubsub = r_client.pubsub(ignore_subscribe_messages=True)
        self._callback = PeriodicCallback(self.get_message, 1)
        self._callback.start()

    def __del__(self):
        # Tell tornado to stop asking as
        self._callback.stop()
        for key in self.channel_listeners:
            self._pubsub.unsubscribe(key)
        self._pubsub.close()

    def subscribe(self, channel, callback):
        """Subscribe a callback to a channel

        Parameters
        ----------
        channel : str
            The channel to register the callback
        callback : function
            The function to be registered

        Returns
        -------
        function
            The function to call in order to unsubscribe from the channel
        """
        # If the current object was not already listening to the channel,
        # subscribe to the channel
        if channel not in self.channel_listeners:
            self._pubsub.subscribe(channel)

        # Add the callback to the channel's listener list
        self.channel_listeners[channel].append(callback)

        # Create the function used to unsubscribe the callback
        def destructor():
            self.channel_listeners[channel].remove(callback)
            # Do some clean-up: if there is no body listen to a channel
            # unsubscribe the object from it
            if len(self.channel_listeners[channel]) == 0:
                self._pubsub.unsubscribe(channel)

        # Return the unsubscribe function
        return destructor

    def get_message(self):
        """Callback for the tornado's IOLoop"""
        # Get a message (if exists)
        message = self._pubsub.get_message()
        if message:
            # There is a message! Execute all the callback functions
            self._notify(message)

    def _notify(self, message):
        """Notify the message to all it's callback functions

        Parameters
        ----------
        message : dict
            The message received
        """
        # Get the channel of the message
        channel = message['channel']
        # Get the actual data
        data = message['data']
        # Call all the callback functions passing the data received
        for callback in self.channel_listeners[channel]:
            callback(data)
