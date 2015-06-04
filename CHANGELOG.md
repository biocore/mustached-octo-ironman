# moi changelog

## Version 0.1.0-dev, changes go here

### Features
* `moi_parent_id` is now available to all executed methods
* `submit` now accepts a `Context` instance
* `_redis_wrap` now returns the result
* `_submit` now returns AsyncResult as well as IDs
* `_redis_wrap` will now reraise if an exception is thrown
* moi_list will no longer attempt to set status if the status node does not exist
* `Context` now knows its name
* added moi.moi_js and moi.moi_list_js to retreive the absolute path to the 
    corresponding .js files
* A new click interface for getting job details
* Added `submit` and `job` methods to the command line interface
* Can get summary information for all user jobs

### Incompatible changes
* `update_status` is now `moi_update_status`
* `_submit` return signature now includes `AsyncResult`
* `moi.init()` now takes a `group_id`, which is sent `onopen` if not null

### Bug fixes
* `moi_context` was the dict of contexts, instead of the context name

## Version 0.1.0, initial release (Nov. 17, 2014)

### Features
* Easy support for submitting compute, and monitoring compute from a browser.
* Communication between jobs -> MOI and MOI -> websocket have been defined.
