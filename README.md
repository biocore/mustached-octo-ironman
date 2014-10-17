mustached-octo-ironman
======================

Easy dispatched compute via in a Tornado environment using Redis and IPython. Updates are readily available to the client-side via a websocket and a customizable div.

This codebase originates from [qiita](https://github.com/biocore/qiita) and is heavily influenced by their dev-team, in particular @squirrelo and @josenavas.

Examples
--------

To submit a job that can update status and publish updates via Redis but does not need to update client-side:

```python
from moi.job import submit_nouser

def hello(**kwargs):
    return "hi!"
    
submit_nouser(hello)
```

To submit a job that is monitored client-side:

```python
from moi.job import submit
from tornado.web import RequestHandler

def hello(**kwargs):
    kwargs['status_update']("I'm about to say hello")
    return "hi!"

class Handler(RequestHandler):
    def get(self):
        result_handler = "/hello_result"
        submit(self.current_user, "The hello job", result_handler, hello)
```

Structure
---------

In `moi`, jobs are associated with a group (e.g., `self.current_user`). A group can have 0 to many jobs. A group has an associated `pubsub` channel that can be used to perform actions on the group.

All groups have a Redis `set` associated under `<group>:jobs` that contain the job IDs associated with the group. Each group also has a `pubsub` at `<group>:pubsub`. The `pubsub` is listened to by the `moi` web socket handler.   

All jobs are keyed in Redis by their ID. In addition, each job has a `pubsub` at the key `<job ID>:pubsub` that can be used to notify subscribers of changes to the job. In `moi`, the web socket handler listens to all job pubsubs.

All communication over `pubsub` channels consists of JSON objects, where the keys are the actions to be performed and the values are communication and/or action dependent.

Group pubsub communication
--------------------------

A group accepts the following actions via `pubsub`:

    add : str or list of str
        Add the job IDs described by each str to the group
    remove : str or list of str
        Remove the job IDs describe by each str from the group
    
Job pubsub communication
------------------------

A job can send the following actions over a `pubsub`:
    
    update : {"status", null}
        If "status", this indicates a change of the job's status. If null, then multiple aspects of the job have been updated.

Job info
--------

Job information can be accessed by using the job ID as the key in Redis. This information is a JSON object that consists of:

    id : str
        A str of a UUID4, the job's ID
    name : str
        The job's name
    handler : str or null
        If not null, this is expected to be a URL that can interpret the result of the job (e.g., /foo)
    group : str
        The group the job is associated with.
    status : str
        The job's status
    Result : str or null
        The result of the job. If the job has not completed, this is null. If the job errors out, this will contain a 
        repr'd version of the traceback

The default status states defined by `moi` are `{"Queued", "Running", "Success", "Failed"}`.

Websocket communication
-----------------------

Communication over the websocket uses JSON and the following protocols. From server to client:

    add : str or list of str
        Add the job IDs described by each str to the moi-joblist
    remove : str or list of str
        Remove the job IDs describe by each str from the moi-joblist
    update : job info object
        Job specific updates
