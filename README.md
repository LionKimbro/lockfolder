# Lock Folder

Obtain a lock by posting a bid into a lock folder, and checking for rivals.

#### Installation

```
pip install lockfolder
```

### How to Use It


```
import pathlib
from lockfolder import lockfolder

lockfolder.init()

p = pathlib.Path("path/to/lockfolder")

if lockfolder.lock(p):
    print("aquired lock")
    ...
    ...
    lockfolder.unlock(p)
else:
    print("failed to aquire lock")
```

Adapt to context manager, throw-finally systems, decorator, what have
you, as you like.


### Lock Files

Lock files are JSON files that are logically equivalent to:

```
----------[ filename: <GUID>.json ]-----------------------------------
  {
    "PID": <integer PID>,
    "CREATED": <integer timestamp>
  }
----------------------------------------------------------------------
```


### Concept

This is a mutex system, that ensures that only one process has access to a resource.

It's defining features are:
* a filesystem folder is used to bid for a lock
* it is cross-platform to contemporary operating systems
* it's very simple
* it has only one external dependency: `psutil`
* it is robust to recycled PIDs

Some of the limitations of this system, are:
* live-locks are possible, which occurs when too many processes all try to get a lock at the same time
   * all petitioners will fail to achieve a lock
   * insistent petitioners should repeat efforts at connection with an exponential backoff
* security and file permissions are not taken account of
   * it is possible for a malicious user or process to manually delete or create lock files
* there is an extremely unlikely possibility of a v4 GUID collision
* PID recycling fails if the same PID is recycled to a competitor within the second (highly unusual) 


### Basic Strategy:

* each process self-assigns a GUID
* each process notes its PID
* each process notes its create-time
* a folder keeps the locks for the resource ("bids" and "locks" are the same thing in this system)
* the procedure is "check-bid-check", and if any check shows another bid/lock, the process deletes its own bid (if it got that far) and returns "fail"
* if the "check-bid-check" passes, then the bid is left until the process completes, at which point the bid is deleted
* bids contain the process PID and creation time of the process, and may be deleted by any process that wishes to challenge a prior bid, provided that it can determine that a process created at <create-time> with process ID <PID> is no longer running
* upon a fail, at the programmer's discretion, processes may delay and retry, with delays having a random component, and increasing duration between attempts


### Procedure:

Here is the basic procedure more specifically:

STEP 10. **CHECK** -- check the lock folder for the presence of any files; if there are files, END (error state: FAIL); if there are no files, proceed to step 20

STEP 20. **BID** -- write a file into the lock folder, containing the following, then proceed to step 30

* filename: `(self-selected-GUID-for-this-process).json`
* JSON file content:
   * PID: `(process-id)`
   * PROCESS-START-TIME: `(timestamp-for-this-process)`

STEP 30. **CHECK** -- check the lock folder for the presence of any files, other than my own: if there are other files, proceed to step 40, otherwise, proceed to step 50

STEP 40. **DELETE & FAIL** -- delete the bid file that was created in step 20, then END (error state: FAIL)

STEP 50. **OPERATE** -- the lock has been acquired (it's the same file as the bid created in step 20) -- do whatever you please with it

STEP 60. **DELETE & END** -- delete the bid file that was created in step 20, then END (error state: SUCCESS)


### Additional Resources

* https://www.reddit.com/r/AskProgramming/comments/186ot93/is_this_checkbidcheck_mutex_strategy_okay/ -- a Reddit thread, in which I requested verification of correctness for this system.

written: 2023-11-29

