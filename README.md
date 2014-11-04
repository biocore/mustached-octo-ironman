mustached-octo-ironman
======================

Easy dispatched compute via in a Tornado environment using Redis and IPython. Updates are readily available to the client-side via a websocket and a customizable div.

This codebase originates from [qiita](https://github.com/biocore/qiita) and is heavily influenced by their dev-team, in particular [@squirrelo](https://github.com/squirrelo) and [@josenavas](https://github.com/josenavas).

Examples
--------

To submit a job that can update status and publish updates via Redis but does not need to update client-side:

```python
from moi.job import submit_nouser

def hello(**kwargs):
    return "hi!"
    
submit_nouser(hello)
```

To submit a job that is can be client-side (assumes the `moi` websocket handler is in place and that `moi.js` is loaded client-side):

```python
from moi import ctx_default
from moi.job import submit
from tornado.web import RequestHandler

def hello(**kwargs):
    kwargs['status_update']("I'm about to say hello")
    return "hi!"

class Handler(RequestHandler):
    def get(self):
        result_handler = "/hello_result"
        submit(ctx_default, self.current_user, "The hello job", result_handler,
               hello)
```

Types of compute
----------------

Any function that can be sent over to an IPython client is acceptable. Going one step further, the code also supports system calls such that any string that is passed will be used in a subprocess call on the executing engine.

Structure
---------

In `moi`, jobs are associated with a group (e.g., `self.current_user`). A group can have 0 to many jobs. A group has an associated `pubsub` channel at `<group>:pubsub` that can be used to perform actions on the group.

All groups have a Redis `set` associated under `<group>:jobs` that contain the job IDs associated with the group.   

All jobs are keyed in Redis by their ID. In addition, each job has a `pubsub` at the key `<job ID>:pubsub` that can be used to notify subscribers of changes to the job. 

All communication over `pubsub` channels consists of JSON objects, where the keys are the actions to be performed and the values are communication and/or action dependent.

Group pubsub communication
--------------------------

A group accepts the following actions via `pubsub`:

    add : {list, set, tuple, generator} of str
        Add the job IDs described by each str to the group
    remove : {list, set, tuple, generator} of str
        Remove the job IDs describe by each str from the group
    get : {list, set, tuple, generator} of str
        Get the job details for the IDs
    
Job pubsub communication
------------------------

A job can send the following actions over a `pubsub`:
    
    update : {list, set, tuple, generator} of str
        Notifies subscribers that the corresponding job has been updated. A job can notify that other jobs have been updated.
        
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
    result : str or null
        The result of the job. If the job has not completed, this is null. If the job errors out, this will contain a 
        repr'd version of the traceback

The default status states defined by `moi` are `{"Queued", "Running", "Success", "Failed"}`.

Websocket communication
-----------------------

Communication over the websocket uses JSON and the following protocols. From server to client:

    add : list of object
        Add the jobs described to the moi-joblist
    remove : list of object
        Remove the jobs described from the moi-joblist
    update : list of object
        Update the jobs described in the moi-joblist
        
From client to server:

    get : list of str
        The IDs that the client would like to get details for
    remove : list of str 
        The IDs that the client would no longer like tracked in the job group
