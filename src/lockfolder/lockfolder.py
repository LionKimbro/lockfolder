"""lockfolder.py  -- mutex strategy using process-identifying GUIDs in folders

  Copyright 2023  Lion Kimbro

  Permission is hereby granted, free of charge, to any person
  obtaining a copy of this software and associated documentation files
  (the “Software”), to deal in the Software without restriction,
  including without limitation the rights to use, copy, modify, merge,
  publish, distribute, sublicense, and/or sell copies of the Software,
  and to permit persons to whom the Software is furnished to do so,
  subject to the following conditions:

  The above copyright notice and this permission notice shall be
  included in all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
  NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
  BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
  ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
  CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.


This is a mutex system.

Proposition:

1. The system never(*) grants a lock to more than one process.
2. Live-locks are acceptable.
3. Security and file permissions are NOT concerns.
4. To work on a system, it requires:
   A. a conventional filesystem
   B. process PIDs, verifiable by other processes
   C. process create times, verifiable by other processes

"never" (*): Failure in the event of v4 GUID collision is acceptable.


Basic strategy:

* each process self-assigns a GUID
* each process notes its PID
* each process notes its create-time
* a folder keeps the locks for the resource ("bids" and "locks" are
  the same thing in this system)
* the procedure is "check-bid-check", and if any check shows another
  bid/lock, the process deletes its own bid (if it got that far) and
  returns "fail"
* if the "check-bid-check" passes, then the bid is left until the
  process completes, at which point the bid is deleted
* bids contain the process PID and creation time of the process, and
  may be deleted by any process that wishes to challenge a prior bid,
  provided that it can determine that a process created at
  <create-time> with process ID <PID> is no longer running
* upon a fail, at the programmer's discretion, processes may delay and
  retry, with delays having a random component, and increasing
  duration between attempts

I have discussed the strategy on Reddit:
https://www.reddit.com/r/AskProgramming/comments/186ot93/is_this_checkbidcheck_mutex_strategy_okay/


Notes about this implementation:

* written for multiple competing processes
* is NOT thread-safe, and not written for multiple competing threads
* assumes that PIDs are not recycled within one second
  -- that is, the precision on recorded process create times is 1 second
  -- the failure story is this:
     If a process places a lock, dies or is killed before it removes
     its lock, and then another process with the same PID is created
     in the same second, (HIGHLY UNLIKELY,) then the "stale lock" will
     not be detected, until this process dies, and is replaced by
     either no process having that PID, or a process with that PID
     created that didn't start in the same second.


The simplest way to use this is as follows:
------------------------------------------------------------------------

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
------------------------------------------------------------------------

Adapt to context manager, throw-finally systems, decorator, what have
you, as you like.


Lock files are JSON files that are logically equivalent to:

----------[ filename: <GUID>.json ]-----------------------------------
  {
    "PID": <integer PID>,
    "CREATED": <integer timestamp>
  }
----------------------------------------------------------------------
"""

import os
import uuid
import json
import pathlib
import psutil


UUID = "UUID"
PID = "PID"
CREATED = "CREATED"


g = {}


def init():
    g[UUID] = str(uuid.uuid4())
    g[PID] = os.getpid()
    g[CREATED] = int(psutil.Process(g[PID]).create_time())


def lock(lockfolder_path):
    """Aquire a lock in folder p.
    
    Returns:
      True -- lock aquired, path to lock file
      False -- lock NOT aquired, try again later
    """
    assert isinstance(lockfolder_path, pathlib.Path)

    bid_path = None

    if not _check(lockfolder_path):
        return False

    _bid(lockfolder_path)

    if not _check(lockfolder_path):
        _delete_bidfile(lockfolder_path)
        return False

    return True


def unlock(lockfolder_path):
    """Release a lock in folder p."""
    _delete_bidfile(lockfolder_path)


def _bidfile_path(lockfolder_path):
    """Create a path to my bid file."""
    filename = g[UUID] + ".json"
    return lockfolder_path / filename


def _delete_bidfile(lockfile_path):
    _bidfile_path(lockfile_path).unlink()


def _bid(lockfolder_path):
    """Create a bid in the current lock folder.
    
    The bid is a JSON file with this structure:

      {
          PID: g[PID],
          CREATED: g[CREATED]
      }

    The filename of the JSON file is:

      g[UUID] + ".json"

    """
    # Construct the filename using UUID
    filepath = _bidfile_path(lockfolder_path)

    # Data to be written to the file
    data = {
        PID: g[PID],
        CREATED: g[CREATED]
    }

    # Writing data to the file
    with open(filepath, 'w') as file:
        json.dump(data, file)


def challenge(p):
    """Challenge a foreign lockfile.
    
    True -- stale lockfile detected and erased
    False -- lockfile was valid
    """
    data = json.loads(p.read_text("utf-8"))
    pid = data[PID]
    lockfile_created_time = data[CREATED]

    # Check if the process is still running
    if not psutil.pid_exists(pid):
        # Process not running, delete lockfile
        os.remove(p)
        return True

    try:
        process = psutil.Process(pid)
        # Get the creation time of the process
        process_created_time = int(process.create_time())

        # Compare the creation time of the lockfile and the process
        if process_created_time != lockfile_created_time:
            # Creation times do not match, delete lockfile
            os.remove(p)
            return True

    except psutil.NoSuchProcess:
        # Process does not exist, delete lockfile
        os.remove(p)
        return True

    # Lockfile is valid
    return False


def _check(lockfolder_path):
    """Check for valid competing bids in the lock folder.
    
    True -- no valid competing bids found
    False -- competing bids: cannot lock resource
    """
    # Iterate over all files in the lock folder
    for p in lockfolder_path.iterdir():
        # Skip non-JSON files
        if p.suffix != '.json':
            continue

        # Check if the file is the current process's own bid
        if p.stem == g[UUID]:
            continue  # This is our own bid, skip it

        # Challenge any other bid found
        if challenge(p):
            # If the competing bid was removed, continue checking for others
            continue
        else:
            # A valid competing bid exists
            return False

    # No valid competing bids found
    return True

