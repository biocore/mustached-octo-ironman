# adapted from
# https://github.com/leporo/tornado-redis/blob/master/demos/websockets
from json import loads, dumps

import toredis
from tornado.web import authenticated
from tornado.websocket import WebSocketHandler
from tornado.gen import engine, Task

from moi import r_client


class MessageHandler(WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(MessageHandler, self).__init__(*args, **kwargs)
        self.toredis = toredis.Client()
        self.toredis.connect()

        self.jobs = set()
        self._listening_to = set()

        self.user_jobs = self.get_current_user() + ':jobs'
        self.user_pubsub = self.get_current_user() + ':pubsub'

        self.listen_for_updates()

    def get_current_user(self):
        user = self.get_secure_cookie("user")
        if user is None:
            raise ValueError("No user associated with the websocket!")
        else:
            return user.strip('" ')

    @authenticated
    def on_message(self, msg):
        msginfo = loads(msg)

        if msginfo == 'first-contact':
            # client has opened a connection, send them the state of their jobs
            payload = self._add_job(r_client.smembers(self.user_jobs))
            self.write_message(dumps({'add': payload}))
            self._send_last_messages()
        elif 'remove' in msginfo:
            print 'removing...', msginfo['remove']
            self._remove_job(msginfo['remove'])

    @authenticated
    def open(self):
        for job_id in r_client.smembers(self.user_jobs):
            self.listen_to_job(job_id)

    def listen_for_updates(self):
        # Attach a callback on the user's pubsub where we get information
        # about new jobs, or jobs to remove
        self.toredis.subscribe(self.user_pubsub, callback=self.callback)

    def listen_to_job(self, job_id):
        # Attach a callback for the job being listened too. This callback is
        # executed when anything is placed onto the channel.
        self.toredis.subscribe(job_id + ':pubsub', callback=self.callback)
        self._listening_to.add(job_id + ':pubsub')

    def _send_job_state(self):
        for jobid in self.jobs:
            msg = r_client.get(jobid)
            if msg:
                self.write_message(msg)

    def callback(self, msg):
        message_type, channel, payload = msg

        if message_type != 'message':
            return

        payload = loads(payload)

        # group details
        if channel == self.user_pubsub:
            for_client = {}

            if 'add' in payload:
                for_client['add'] = self._add_job(payload['add'])

            if 'remove' in payload:
                for_client['remove'] = self._remove_job(payload['remove'])

        # job details
        elif channel in self._listening_to:
            self.write_message(payload)

    def _add_job(self, job_ids):
        if not isinstance(job_ids, (list, set)):
            job_ids = [job_ids]

        for_client = []

        for job_id in job_ids:
            job_pubsub = job_id + ':pubsub'
            self.listen_to_job(job_id)
            details = {'id': job_id,
                       'name': r_client.get(job_id + ':name'),
                       'status': r_client.get(job_id + ':status')}
            for_client.append(details)
        return for_client

    def _remove_job(self, job_ids):
        """Remove a job or jobs

        Parameters
        ----------
        job_ids : str or list of str
            The job ID or job IDs to remove
        """
        if not isinstance(job_ids, (list, set)):
            job_ids = [job_ids]

        jobs_removed = []
        for job_id in job_ids:
            job_pubsub = job_id + ':pubsub'
            if job_pubsub in self._listening_to:
                self._listening_to.remove(job_pubsub)
                r_client.srem(self.user_jobs, job_id)
                self.toredis.unsubscribe(job_pubsub)
                jobs_removed.append(job_id)

        return jobs_removed

    @engine
    def on_close(self):
        for channel in self._listening_to:
            yield Task(self.toredis.unsubscribe, channel)
        yield Task(self.toredis.unsubscribe, self.user_pubsub)

        self.redis.disconnect()
