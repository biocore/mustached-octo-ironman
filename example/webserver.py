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

from moi import r_client
from moi.websocket import MOIMessageHandler
from moi.job import submit


define("port", default=8888, help="run on the given port", type=int)


DIRNAME = dirname(__file__)
STATIC_PATH = join(DIRNAME, ".")
COOKIE_SECRET = b64encode(uuid4().bytes + uuid4().bytes)


def say_hello(name, **kwargs):
    from time import sleep
    kwargs['update_status']("I'm about to say hello")
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
        self.render("moi_example.html", user=self.get_current_user())

    def post(self):
        name = self.get_argument("jobname", "noname")
        handler = "/result"
        group = "no-user"
        argument = name

        submit(group, name, handler, say_hello, argument)
        self.redirect('/')


class ResultHandler(RequestHandler):
    def get(self, id):
        job_info = loads(r_client.get(id))
        self.render("moi_result.html", job_info=job_info)


class MOIApplication(Application):
    def __init__(self):
        handlers = [
            (r"/moi-ws/", MOIMessageHandler),
            (r"/static/(.*)", StaticFileHandler,
             {"path": STATIC_PATH}),
            (r"/result/(.*)", ResultHandler),
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
