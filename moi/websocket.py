# adapted from
# https://github.com/leporo/tornado-redis/blob/master/demos/websockets
from tornado.web import authenticated
from tornado.websocket import WebSocketHandler
from tornado.escape import json_encode, json_decode

from moi.group import Group

clients = set()

class MOIMessageHandler(WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(MOIMessageHandler, self).__init__(*args, **kwargs)
        self.group = Group(self.get_current_user(), forwarder=self.forward)

    def get_current_user(self):
        user = self.get_secure_cookie("user")
        if user is None:
            raise ValueError("No user associated with the websocket!")
        else:
            return user.strip('" ')

    @authenticated
    def on_message(self, msg):
        """Accept a message that was published, process and forward

        Parameters
        ----------
        msg : str
            The message sent over the line

        Notes
        -----
        This method only handles messages where `message_type` is "message".
        """
        if self not in clients:
            return

        try:
            payload = json_decode(msg)
        except ValueError:
            # unable to decode so we cannot handle the message
            return

        for verb, args in payload.items():
            self.group.action(verb, args)

    def open(self):
        clients.add(self)

    def on_close(self):
        clients.remove(self)
        self.group.close()

    def forward(self, payload):
        self.write_message(json_encode(payload))
