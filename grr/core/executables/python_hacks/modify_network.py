#!/usr/bin/env python
"""Shut down windows hosts."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import platform
import re


def NetshStaticIp(interface,
                  ip=u'127.0.0.9',
                  subnet=u'255.255.255.255',
                  gw=u'127.0.0.1'):
  """Changes interface to a staticly set IP.

  Sets IP configs to local if no paramaters passed.

  Args:
    interface: Name of the interface.
    ip: IP address.
    subnet: Subnet mask.
    gw: IP address of the default gateway.

  Returns:
    A tuple of stdout, stderr, exit_status.
  """
  args = [
      '/c', 'netsh', 'interface', 'ip', 'set', 'address', interface, 'static',
      ip, subnet, gw, '1'
  ]
  # pylint: disable=undefined-variable
  res = client_utils_common.Execute(
      'cmd', args, time_limit=-1, bypass_whitelist=True)
  return res


def DisableInterfaces(interface):
  """Tries to disable an interface.  Only works on Vista and 7.

  Args:
    interface: Name of the interface to disable.

  Returns:
    res which is a tuple of (stdout, stderr, exit_status, time_taken).
  """
  set_tested_versions = ['vista', '2008']
  set_args = ['/c', 'netsh', 'set', 'interface', interface, 'DISABLED']
  host_version = platform.platform().lower()
  for version in set_tested_versions:
    if host_version.find(version) != -1:
      # pylint: disable=undefined-variable
      res = client_utils_common.Execute(
          'cmd', set_args, time_limit=-1, bypass_whitelist=True)
      return res
  return ('', 'Command not available for this version.', 99, '')


def GetEnabledInterfaces():
  """Gives a list of enabled interfaces. Should work on all windows versions.

  Returns:
    interfaces: Names of interfaces found enabled.
  """
  interfaces = []
  show_args = ['/c', 'netsh', 'show', 'interface']
  # pylint: disable=undefined-variable
  res = client_utils_common.Execute(
      'cmd', show_args, time_limit=-1, bypass_whitelist=True)
  pattern = re.compile(r'\s*')
  for line in res[0].split('\r\n'):  # res[0] is stdout.
    interface_info = pattern.split(line)
    if 'Enabled' in interface_info:
      interfaces.extend(interface_info[-1:])
  return interfaces


def MsgUser(msg):
  """Sends a message to a user.

  Args:
    msg: Message to be displaied to user.

  Returns:
    res which is a tuple of (stdout, stderr, exit_status, time_taken).
  """
  msg_tested_versions = ['xp', 'vista', '2008', '2003']
  msg_args = ['/c', '%SystemRoot%\\System32\\msg.exe', '*', '/TIME:0']
  host_version = platform.platform().lower()
  if not msg:
    return ('Command not ran.', 'Empty message.', -1)
  else:
    msg_args.extend([msg])
  for version in msg_tested_versions:
    if host_version.find(version) != -1:
      # pylint: disable=undefined-variable
      res = client_utils_common.Execute(
          'cmd', msg_args, time_limit=-1, bypass_whitelist=True)
      return res
  return ('', 'Command not available for this version.', -1)


def main():
  return_str = {}
  # pylint: disable=g-bad-name
  MSG_STRING = ('***WARNING for Acme Corp Security***\n'
                'Your machine was found to be infected with a \n'
                'very scary virus. As a security measure we are \n'
                'shutting down your internet connection. Please \n'
                'call 0800-OHNOES immediately.')
  # pylint: disable=undefined-variable
  if 'msg' in py_args:
    return_str['msg'] = MsgUser(py_args['msg'])
  else:
    return_str['msg'] = MsgUser(MSG_STRING)

  for interface in GetEnabledInterfaces():
    if interface != 'Loopback' or interface != 'Internal':
      return_str[interface] = DisableInterfaces(interface)
      # Disabaling interface is not available.
      # Change interface config to be unroutable.
      if return_str[interface][2] == 99:
        if all([key in py_args for key in ['ip', 'subnet', 'gw']]):
          return_str[interface] = NetshStaticIp(
              interface, py_args['ip'], py_args['subnet'], py_args['gw'])
        else:
          return_str[interface] = NetshStaticIp(interface)

  # Build magic string.
  magic_list = []
  for key in return_str:
    stdout, stderr, exit_status, time_taken = return_str[key]
    key_str = '%s, %s, %s, %s, %s' % (key, stdout.encode('base64'),
                                      stderr.encode('base64'), exit_status,
                                      time_taken)
    magic_list.append(key_str)

  magic_return_str = ''.join(magic_list)  # pylint: disable=unused-variable


if __name__ == '__main__':
  main()
