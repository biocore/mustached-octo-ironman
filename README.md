mustached-octo-ironman
======================

Easy dispatched compute via in a Tornado environment using Redis and IPython. Updates are readily available to the client-side via a websocket and a customizable div.

Examples
--------

To submit a basic job without monitoring it:

```python
from moi import unmonitored_submit, r_client

def hello():
    return "hi!"
    
job_id = unmonitored_submit(hello)
```

To submit a job that is monitored client-side:

```python
from moi import submit
from tornado.web import RequestHandler

def hello(**kwargs):
    kwargs['status_update']("I'm about to say hello")
    return "hi!"

class Handler(RequestHandler):
    def get(self):
        result_handler = "/hello_result"
        submit(self.current_user, "The hello job", result_handler, hello)
```
