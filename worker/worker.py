#!/usr/bin/env python
"""This is a backend analysis worker which will be deployed on the server.

We basically pull a new task from the task master, and run the plugin
it specifies.
"""


import multiprocessing
import time

import logging

# pylint: disable=unused-import,g-bad-import-order
from grr.lib import server_plugins
# pylint: enable=unused-import,g-bad-import-order

from grr.lib import access_control
from grr.lib import config_lib
from grr.lib import flags
from grr.lib import startup
from grr.lib import worker


def main(unused_argv):
  """Main."""
  config_lib.CONFIG.AddContext(
      "Worker Context",
      "Context applied when running a worker.")

  # Initialise flows
  startup.Init()

  workers = {}
  dead_count = 0
  start_time = time.time()

  if config_lib.CONFIG["Worker.worker_process_count"] <= 1:
    # Special case when we only support a single worker process and don't need
    # the complexity of multiprocessing.
    StartWorker()
  else:
    # Run a pool of workers, reviving any that die and logging the death.
    while True:
      # Start any required new workers.
      while len(workers) < config_lib.CONFIG["Worker.worker_process_count"]:
        worker_process = multiprocessing.Process(target=StartWorker)
        worker_process.start()
        logging.debug("Added new worker %d", worker_process.pid)
        workers[worker_process.name] = worker_process

      # Kill off any dead workers.
      dead_workers = []
      for worker_name, worker_process in workers.items():
        if not worker_process.is_alive():
          logging.error("Worker %s is dead", worker_process.pid)
          dead_workers.append(worker_name)
          dead_count += 1
      for worker_name in dead_workers:
        del workers[worker_name]

      # Catch all workers dying on startup and raise immediately instead of
      # continuously respawning them.
      if (time.time() - start_time) < 60:
        if dead_count >= config_lib.CONFIG["Worker.worker_process_count"]:
          for worker_process in workers.values():
            worker_process.terminate()
          raise RuntimeError("Workers did not start up, all of them died.")

      time.sleep(10)


def StartWorker():
  token = access_control.ACLToken(username="GRRWorker")
  worker_obj = worker.GRRWorker(queue=worker.DEFAULT_WORKER_QUEUE,
                                token=token)
  worker_obj.Run()

if __name__ == "__main__":
  flags.StartMain(main)
