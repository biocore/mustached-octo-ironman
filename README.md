mustached-octo-ironman
======================

Easy dispatched compute via in a Tornado environment using Redis and IPython. Updates are readily available to the client-side via a websocket and a customizable div. The specific goals of `moi` are:

* make compute as easy as possible for the developer
* automatically propagate job information to end user without requiring developer intervention
* define the communication protocols for compute -> server, and server <-> web client

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

Almost function that can be sent over to an IPython client is acceptable. The two expectations are:

* The function accepts `\*\*kwargs`
* The function raises an exception (doesn't matter what) if the function "failed"

Going one step further, the code also supports system calls through a special function `moi.job.system_call`, where the argument being passed is the command to run. 

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

Job organization
----------------

Jobs are described in a hierarchy to allow jobs to be associated with multiple logically related groups. For instance, a job might be associated with a user, and additionally, associated with a workflow that the user is executing (e.g., some complex analysis). The hierarchy can be thought of as a tree, where internal nodes are "groups" and the tips are actual jobs. Paths in the tree are denoted by a ":" delimited string. For instance `foo` is the group "foo", while `foo:ID_1:ID_2` denotes the group "foo", which contains "ID_1", which contains "ID_2". Groups are described by uuid's, as are jobs. 
        
Info object
-----------

Job and group information can be accessed by using the ID as the key in Redis. This information is a JSON object that consists of:

    id : str
        A str of a UUID4, the ID
    name : str
        The group or job name
    type : str, {'job', 'group'}
        What type of info object this is.
    pubsub : str
        The pubsub for this info object
    url : str or null
        The URL for group or job results. This URL is provided the corresponding ID (e.g., /foo/<uuid>).
    parent : str or null
        The ID of the parent. Null if the group is the root. It is not required that this be a uuid.
    status : str
        The group or job status
    result : str or null
        The result of the job. If the job has not completed, this is null. If the job errors out, this will contain a 
        repr'd version of the traceback. This is null if the object described a group.
    date_start : str of time
        Time when the job started, expected format is %Y-%m-%d %H:%M:%s. This is null if the object describes a group.
    date_end : str of time
        Time when the job ended, expected format is %Y-%m-%d %H:%M:%s. This is null if the object described a group.
    
The default status states defined by `moi` are `{"Queued", "Running", "Success", "Failed"}`.

Websocket communication
-----------------------

Communication over the websocket uses JSON and the following protocols. From server to client:

    add : info object
        An info object to that has been added on the server.
    remove : info object
        An info object that has been removed on the server.
    update : info object
        An info object that has been upadted on the server.
        
From client to server:

    remove : str
        An ID that the client would like to remove. If a group ID, then all descending jobs are removed as well.
