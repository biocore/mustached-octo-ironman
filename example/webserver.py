# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from os.path import join, dirname
from base64 import b64encode
from uuid import uuid4
from json import loads

import tornado
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.options import define, options, parse_command_line
from tornado.web import RequestHandler, StaticFileHandler
from tornado.escape import json_encode

from moi import r_client, ctx_default
from moi.websocket import MOIMessageHandler
from moi.job import submit
from moi.group import get_id_from_user, create_info


define("port", default=8886, help="run on the given port", type=int)


DIRNAME = dirname(__file__)
STATIC_PATH = join(DIRNAME, ".")
COOKIE_SECRET = b64encode(uuid4().bytes + uuid4().bytes)


def say_hello(name, **kwargs):
    from time import sleep
    kwargs['moi_update_status']("I'm about to say hello")
    sleep(5)
    return "hello from %s!" % name


class SubmitHandler(RequestHandler):
    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", json_encode(user))
        else:
            self.clear_cookie("user")

    def get(self):
        self.set_current_user("no-user")
        group_id = get_id_from_user("no-user")
        self.render("moi_example.html", user=self.get_current_user(),
                    group_id=group_id)

    def post(self):
        name = self.get_argument("jobname", None)
        group_name = self.get_argument("jobgroup", None)
        parent = get_id_from_user("no-user")
        job_url = "/result"

        if name is not None:
            submit(ctx_default, parent, name, job_url, say_hello, name)
        else:
            group_url = "/group"
            group = create_info(group_name, 'group', url=group_url,
                                parent=parent, store=True)
            group_id = group['id']

            for i in range(5):
                name = group_name + '-%d' % i
                submit(ctx_default, group_id, name, job_url, say_hello, name)

        self.redirect('/')


class ResultHandler(RequestHandler):
    def get(self, id):
        job_info = loads(r_client.get(id))
        self.render("moi_result.html", job_info=job_info,
                    group_id=job_info['parent'])


class GroupHandler(RequestHandler):
    def get(self, id):
        self.render("moi_group.html", group_id=id)


class MOIApplication(Application):
    def __init__(self):
        handlers = [
            (r"/moi-ws/", MOIMessageHandler),
            (r"/static/(.*)", StaticFileHandler,
             {"path": STATIC_PATH}),
            (r"/result/(.*)", ResultHandler),
            (r"/group/(.*)", GroupHandler),
            (r".*", SubmitHandler)
        ]
        settings = {
            "debug": True,
            "cookie_secret": COOKIE_SECRET,
            "login_url": "/"
        }
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    parse_command_line()
    http_server = HTTPServer(MOIApplication())
    http_server.listen(options.port)
    print("Tornado started on port", options.port)
    IOLoop.instance().start()


if __name__ == "__main__":
    main()
