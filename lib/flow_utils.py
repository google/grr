#!/usr/bin/env python
"""Utils for flow related tasks."""

import time

import logging

from grr.lib import aff4
from grr.lib import flow

# How long to wait, by default, for a flow to finish.
DEFAULT_TIMEOUT = 650


def GetUserInfo(client, user):
  """Get a User protobuf for a specific user.

  Args:
    client: A VFSGRRClient object.
    user: Username as string. May contain domain like DOMAIN\\user.
  Returns:
    A User rdfvalue or None
  """
  if "\\" in user:
    domain, user = user.split("\\", 1)
    users = [u for u in client.Get(client.Schema.USER, []) if u.username == user
             and u.domain == domain]
  else:
    users = [u for u in client.Get(client.Schema.USER, [])
             if u.username == user]

  if not users:
    return
  else:
    return users[0]


def UpdateVFSFileAndWait(client_id, vfs_file_urn, token=None,
                         timeout=DEFAULT_TIMEOUT):
  """Waits for a file to be updated on the client.

  Calls the UpdateVFSFile flow on a urn and waits for both it and the
  ListDirectory flow it calls to finish.

  Note that this is needed because any flows UpdateVFSFile calls via
  VFS Update methods will not become child flows of UpdateVFSFile,
  and therefore waiting for UpdateVFSFile to complete is not enough.

  Args:
    client_id: Which client to run the flow on.
    vfs_file_urn: Path to VFSFile to update.
    token: The datastore access token.
    timeout: How long to wait for a flow to finish, maximum.
  """
  # Wait for the UpdateVFSFile flow.
  update_flow_urn = StartFlowAndWait(client_id, token=token,
                                     timeout=timeout,
                                     flow_name="UpdateVFSFile",
                                     vfs_file_urn=vfs_file_urn)

  update_flow_obj = aff4.FACTORY.Open(update_flow_urn, token=token,
                                      aff4_type="GRRFlow")

  # Get the child flow so we can wait for it too.
  sub_flow_urn = update_flow_obj.state.get_file_flow_urn

  # If there was no subflow, no need to wait for it.
  if not sub_flow_urn:
    return

  WaitForFlow(sub_flow_urn, token=token,
              timeout=timeout)


def WaitForFlow(flow_urn, token=None, timeout=DEFAULT_TIMEOUT, max_sleep_time=1,
                min_sleep_time=0.2, dampening_multiplier=0.9):
  """Waits for a flow to finish, polling while we wait.

  Args:
    flow_urn: The urn of the flow to wait for.
    token: The datastore access token.
    timeout: How long to wait before giving up, usually because the client has
    gone away.
    max_sleep_time: The initial and longest time to wait in between polls.
    min_sleep_time: The final and shortest time to wait in between polls.
    dampening_multiplier: The current sleep time is multiplied by this number on
    each iteration. Controls how fast the polling reaches its minimum
    sleep time. You probably want this to be less than 1, unless you want
    to wait an increasing amount of time in between flows.

  Raises:
    IOError: If we time out while waiting for the client.
  """

  start_time = time.time()
  sleep_time = max_sleep_time
  while True:
    # Reopen the AFF4Object to check if its status has changed, and also make
    # sure it's a flow.
    with aff4.FACTORY.Open(
        flow_urn, token=token, aff4_type="GRRFlow") as flow_obj:

      # Stop if the flow is done or has timed out.
      if time.time() - start_time > timeout:
        logging.warn("Timed out after waiting %ss for %s!",
                     timeout, flow_obj)
        raise IOError("Timed out trying to access client! Is it connected?")
      if not flow_obj.GetRunner().IsRunning():
        break
    # Decrease the time we sleep each iteration.
    sleep_time = max(sleep_time * dampening_multiplier,
                     min_sleep_time)
    time.sleep(sleep_time)
    logging.debug("Waiting for %s, sleeping for %.3fs", flow_obj, sleep_time)


def StartFlowAndWait(client_id, token=None, timeout=DEFAULT_TIMEOUT,
                     **flow_args):
  """Runs a flow and waits for it to finish.

  Args:
    client_id: The client id of the client to run on.
    token: The datastore access token.
    timeout: How long to wait for a flow to complete, maximum.
    **flow_args: Pass through to flow.

  Returns:
    The urn of the flow that was run.
  """
  flow_urn = flow.GRRFlow.StartFlow(client_id=client_id,
                                    token=token,
                                    sync=True,
                                    **flow_args)

  WaitForFlow(flow_urn, token=token, timeout=timeout)

  return flow_urn


# TODO(user): Deprecate this function once Browser History is Artifacted.
def InterpolatePath(path, client, users=None, path_args=None, depth=0):
  """Take a string as a path on a client and interpolate with client data.

  Args:
    path: A single string/unicode to be interpolated.
    client: A VFSGRRClient object.
    users: A list of string usernames, or None.
    path_args: A dict of additional args to use in interpolation. These take
        precedence over any system provided variables.
    depth: A counter for recursion depth.

  Returns:
    A single string if users is None, otherwise a list of strings.
  """

  sys_formatters = {
      # TODO(user): Collect this during discovery from the registry.
      # HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\
      # Value: SystemRoot
      "systemroot": "c:\\Windows"
  }

  # Override any system formatters with path_args.
  if path_args:
    sys_formatters.update(path_args)

  if users:
    results = []
    for user in users:
      # Extract and interpolate user specific formatters.
      user = GetUserInfo(client, user)
      if user:
        formatters = dict((x.name, y) for x, y in user.ListSetFields())
        special_folders = dict(
            (x.name, y) for x, y in user.special_folders.ListSetFields())

        formatters.update(special_folders)
        formatters.update(sys_formatters)
        try:
          results.append(path.format(**formatters))
        except KeyError:
          pass   # We may be missing values for some users.
    return results
  else:
    try:
      path = path.format(**sys_formatters)
    except KeyError:
      logging.warn("Failed path interpolation on %s", path)
      return ""
    if "{" in path and depth < 10:
      path = InterpolatePath(path, client=client, users=users,
                             path_args=path_args, depth=depth + 1)
    return path
