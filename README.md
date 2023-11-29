## Lock Folder -- README.md
written: 2023-11-29

#### Project Summary
> check-bid-check into a lock folder, to obtain a lock

#### Installation

"pip install lockfolder"

## Concept

_The following description is copied from https://www.reddit.com/r/AskProgramming/comments/186ot93/is_this_checkbidcheck_mutex_strategy_okay/ , where I described this project to Reddit._


I'm writing a mutex system, that I intend to publish to PyPI, and I want to make sure it's right.  But I know that these things can be tricky, so I want to check if anybody can identify important flaws with my strategy.

### Goals:

* it never fails, if a lock is granted and all procedures and promises are kept
   * failure in the event of v4 GUID collision is acceptable
* **live-locks are acceptable**
   * (undestood to be, in crudly expressed terms: "so many things are going for the resource, and they are fighting so intensely, that nobody gets to have the resource")
* security and file permissions are NOT concerns
* it works on any system with a conventional filesystem and conventional process identification (PIDs, & create-time for processes available)

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

* filename: "<self-selected-GUID-for-this-process>.json"
* JSON file content:
   * PID: <process-id>
   * PROCESS-START-TIME: <timestamp-for-this-process>

STEP 30. **CHECK** -- check the lock folder for the presence of any files, other than my own: if there are other files, proceed to step 40, otherwise, proceed to step 50

STEP 40. **DELETE & FAIL** -- delete the bid file that was created in step 20, then END (error state: FAIL)

STEP 50. **OPERATE** -- the lock has been acquired (it's the same file as the bid created in step 20) -- do whatever you please with it

STEP 60. **DELETE & END** -- delete the bid file that was created in step 20, then END (error state: SUCCESS)

### Verification:

My belief is that this procedure should work.

Here's why:

A reference BID (step 20) is completed at time (t1), followed by a CHECK (step 30) initiated at time (t2).

A competing BID is completed in one of three possible time frames:

1. before (t1)
2. after (t1), before (t2)
3. after (t2)

Now we can look at each possible scenario for the competing CHECK.

CASE 1. BID completes before (t1)
* CASE 1.A. CHECK initiated before (t1)
* CASE 1.B. CHECK initiated after (t1), before (t2)
* CASE 1.C. CHECK initiated after (t2)

CASE 2. BID completes after (t1), before (t2)
* CASE 2.A. CHECK initiated after (t1), before (t2)
* CASE 2.B. CHECK initiated after (t2)

CASE 3. BID completes after (t2)
* CASE 3.A. CHECK  - initiated after (t2)

In every case, it can be manually verified that the code logic will prevent dual-assignment of the lock.

* 1.A, B, and C: the reference CHECK will detect two bids, and withdraw its bid (OK)
* 2.A, B: the reference CHECK will detect two bids, and withdraw its bid (OK)
* 3.A: the competing CHECK will detect two bids, and withdraw its bid (OK)

So it seems to me like this should always work.  But I'm only a lay-person at the examination of this logic, and I think there may be important factors that I'm not aware of.

Do you see any problems with this mutex strategy?

* Perhaps there's something tricky about filesystem caching that I am not aware of?
* Perhaps there's some timing issue that I have not properly understood?
* Perhaps my math is wrong?
