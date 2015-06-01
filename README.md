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

Command line interface
======================

moi supports submission of arbitrary system calls and somewhat arbitrary Python code from the command line. Below is an example of sending some Python code. There are a few things to note, first that the `return` allows you to store data in the `result` field of a moi job. Second, we're using `--block` which will halt until the command completes, and then dump the associated job details. 

```bash
$ moi submit --cmd "x = 5; return x + 10" --block
Submitted job id: 0c1ce595-4f6d-4fcb-b872-90118f6b1cd9
********** 0c1ce595-4f6d-4fcb-b872-90118f6b1cd9 **********
context		: default
date_created	: 2015-06-01 15:46:49.977480
date_end	: 2015-06-01 15:46:49.981942
date_start	: 2015-06-01 15:46:49.981620
id		: 0c1ce595-4f6d-4fcb-b872-90118f6b1cd9
name		: no-user-cmd-submit
parent		: ac97957a-a658-47c8-bfaf-08d965b3e745
pubsub		: 0c1ce595-4f6d-4fcb-b872-90118f6b1cd9:pubsub
status		: Success
type		: job
url		: None
result		: 15
```

These jobs are submitted within the relevant context which can be provided on the command line. Next is an example of a system call via moi:

```bash
$ moi submit --cmd "echo 'hello from moi'" --block --cmd-type=system
Submitted job id: 3cb7c548-895a-48ac-b1dc-786e89476c97
********** 3cb7c548-895a-48ac-b1dc-786e89476c97 **********
context		: default
date_created	: 2015-06-01 15:39:17.829820
date_end	: 2015-06-01 15:39:17.840456
date_start	: 2015-06-01 15:39:17.834566
id		: 3cb7c548-895a-48ac-b1dc-786e89476c97
name		: no-user-cmd-submit
parent		: ac97957a-a658-47c8-bfaf-08d965b3e745
pubsub		: 3cb7c548-895a-48ac-b1dc-786e89476c97:pubsub
status		: Success
type		: job
url		: None
result		: [u'hello from moi\n', u'', 0]
```

Blocking and error command line example
=======================================

Now, lets say we have some long running work that we want to kick off, and come back to later. The next example shows a system call that blocks for some extended period, and in the interest of showing what happens when a command fails, we're going to force the command to do something wrong. Note, we are not using `--block`.

```bash
$ moi submit --cmd "sleep 10; foobar" --cmd-type=system
Submitted job id: 088c98fb-8612-43af-80df-1f64555531be
```

Control immediately returns, but let's check the job status while it's "running".

```bash
$ moi job --job-id=088c98fb-8612-43af-80df-1f64555531be
********** 088c98fb-8612-43af-80df-1f64555531be **********
context		: default
date_created	: 2015-06-01 15:51:21.979308
date_end	: None
date_start	: 2015-06-01 15:51:21.983198
id		: 088c98fb-8612-43af-80df-1f64555531be
name		: no-user-cmd-submit
parent		: ac97957a-a658-47c8-bfaf-08d965b3e745
pubsub		: 088c98fb-8612-43af-80df-1f64555531be:pubsub
status		: Running
type		: job
url		: None
result		: None
```

We can see that it has a status of "Running" right now. If we give it a few more seconds, we can see the job finishes. But, since the command `foobar` doesn't exist, we get our error output.

```bash
$ moi job --job-id=088c98fb-8612-43af-80df-1f64555531be
********** 088c98fb-8612-43af-80df-1f64555531be **********
context		: default
date_created	: 2015-06-01 15:51:21.979308
date_end	: 2015-06-01 15:51:32.004002
date_start	: 2015-06-01 15:51:21.983198
id		: 088c98fb-8612-43af-80df-1f64555531be
name		: no-user-cmd-submit
parent		: ac97957a-a658-47c8-bfaf-08d965b3e745
pubsub		: 088c98fb-8612-43af-80df-1f64555531be:pubsub
status		: Failed
type		: job
url		: None
result		: Traceback (most recent call last):
  File "/Users/mcdonadt/ResearchWork/software/mustached-octo-ironman/moi/job.py", line 140, in _redis_wrap
    result = func(*args, **kwargs)
  File "./moi", line 33, in _system_exec
  File "/Users/mcdonadt/ResearchWork/software/mustached-octo-ironman/moi/job.py", line 52, in system_call
    (cmd, stdout, stderr))
ValueError: Failed to execute: sleep 10; foobar
stdout:
stderr: /bin/sh: foobar: command not found
```

Retrieving user job information
-------------------------------

moi can retrieve all the information it knows about a user's jobs and dump it.
In this example, we're going to submit two jobs, one that works and one that 
fails, and then take a look at the resulting output.

First, next start with a user that doesn't exist. Notice the argument is 
`--key` as you can specify the user's UUID or the username.

```bash
$ moi userjobs --key=example
Unknown key: example
```

So we're starting on a clean slate. Now, let's submit some work. The first job
hopefully will succeed and the second probably will crash and burn a horrible
fiery death.

```bash
$ moi submit --user=example --cmd "return 42"
Submitted job id: 558de7a9-fb99-4a67-8b27-62b2ddfb80ff
$ moi submit --user=example --cmd "return float('crash and burn')"
Submitted job id: 44650179-deda-4f5c-9c92-5802f7b13154
```

Now we can examine what happened! The job information is provided below, and
will be sorted by date.

```bash
$ ./moi userjobs --key=example
********** 558de7a9-fb99-4a67-8b27-62b2ddfb80ff **********
context     : default
date_created    : 2015-06-01 16:13:16.499326
date_end    : 2015-06-01 16:13:16.503163
date_start  : 2015-06-01 16:13:16.502835
id      : 558de7a9-fb99-4a67-8b27-62b2ddfb80ff
name        : no-user-cmd-submit
parent      : effc00bd-d9be-4bfa-b788-a273e1c7d5da
pubsub      : 558de7a9-fb99-4a67-8b27-62b2ddfb80ff:pubsub
status      : Success
type        : job
url     : None
result      : 42

********** 44650179-deda-4f5c-9c92-5802f7b13154 **********
context     : default
date_created    : 2015-06-01 16:13:21.959556
date_end    : 2015-06-01 16:13:21.963721
date_start  : 2015-06-01 16:13:21.963070
id      : 44650179-deda-4f5c-9c92-5802f7b13154
name        : no-user-cmd-submit
parent      : effc00bd-d9be-4bfa-b788-a273e1c7d5da
pubsub      : 44650179-deda-4f5c-9c92-5802f7b13154:pubsub
status      : Failed
type        : job
url     : None
result      : Traceback (most recent call last):
  File "/Users/mcdonadt/ResearchWork/software/mustached-octo-ironman/moi/job.py", line 140, in _redis_wrap
    result = func(*args, **kwargs)
  File "./moi", line 27, in _python_exec
  File "<string>", line 1, in execwrapper
ValueError: could not convert string to float: crash and burn
```

But that can be quite a bit of information if the user has a large number of
jobs associated. So we can also just dump a lighter summary that is still 
sorted by time of run.

```bash
$ moi userjobs --key=example --summary
date: 2015-06-01 16:13:16.499326    id: 558de7a9-fb99-4a67-8b27-62b2ddfb80ff    status: Success
date: 2015-06-01 16:13:21.959556    id: 44650179-deda-4f5c-9c92-5802f7b13154    status: Failed
```

Types of compute
----------------

Almost function that can be sent over to an IPython client is acceptable. The two expectations are:

* The function accepts `**kwargs`
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
