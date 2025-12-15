#!/usr/bin/env python
"""Module that contains representers for values returned by Python API."""
import ipaddress
import os
from typing import Any, Optional, Union

import humanize
import IPython
from IPython.lib import pretty

from grr_colab import convert
from grr_colab._textify import client
from grr_colab._textify import stat
from grr_response_proto import jobs_pb2
from grr_response_proto import osquery_pb2
from grr_response_proto import sysinfo_pb2


def register_representers():
  ipython = IPython.get_ipython()
  pretty_formatter = ipython.display_formatter.formatters['text/plain']

  pretty_formatter.for_type(jobs_pb2.StatEntry, stat_entry_pretty)
  pretty_formatter.for_type(jobs_pb2.BufferReference, buffer_reference_pretty)
  pretty_formatter.for_type(sysinfo_pb2.Process, process_pretty)
  pretty_formatter.for_type(jobs_pb2.NetworkAddress, network_address_pretty)
  pretty_formatter.for_type(jobs_pb2.Interface, interface_pretty)
  pretty_formatter.for_type(osquery_pb2.OsqueryTable, osquery_table_pretty)


def stat_entry_pretty(stat_entry: jobs_pb2.StatEntry, p: pretty.PrettyPrinter,
                      cycle: bool) -> None:
  del cycle  # Unused.
  p.text(str(_StatEntryData(stat_entry)))


def buffer_reference_pretty(ref: jobs_pb2.BufferReference,
                            p: pretty.PrettyPrinter, cycle: bool) -> None:
  del cycle  # Unused.
  p.text(str(_BufferReferenceData(ref)))


def process_pretty(process: sysinfo_pb2.Process, p: pretty.PrettyPrinter,
                   cycle: bool) -> None:
  del cycle  # Unused.
  p.text(str(_ProcessData(process)))


def network_address_pretty(address: jobs_pb2.NetworkAddress,
                           p: pretty.PrettyPrinter, cycle: bool) -> None:
  del cycle  # Unused.
  p.text(str(_NetworkAddressData(address)))


def interface_pretty(iface: jobs_pb2.Interface, p: pretty.PrettyPrinter,
                     cycle: bool) -> None:
  del cycle  # Unused.
  p.text(pretty.pretty(_InterfaceData(iface)))


def osquery_table_pretty(table: osquery_pb2.OsqueryTable,
                         p: pretty.PrettyPrinter, cycle: bool) -> None:
  del cycle  # Unused.
  df = convert.from_osquery_table(table)
  p.text(str(df))


class _RepresenterList(list):
  """Parent of representer lists that ensures that slices have the same type."""

  def __getitem__(self, key: Union[int, slice]) -> Union[Any, list[Any]]:
    if isinstance(key, slice):
      return type(self)(super().__getitem__(key))
    return super().__getitem__(key)


class StatEntryList(_RepresenterList):
  """Representer for a list of stat entries."""

  def __init__(self, *args, **kwargs) -> None:
    super().__init__(*args, **kwargs)
    self._hierarchy: Optional[dict[str, list]] = None
    self._build_hierarchy()

  def _build_hierarchy(self) -> None:
    """Builds hierarchy of stat entries in list.

    Returns:
      Nothing.
    """
    self._hierarchy = {'': []}
    items = sorted(self, key=lambda _: _.pathspec.path)

    for stat_entry in items:
      path = os.path.normpath(stat_entry.pathspec.path)
      parent = os.path.dirname(path)
      if parent not in self._hierarchy:
        self._hierarchy[parent] = []
        self._hierarchy[''].append((parent, None))
      self._hierarchy[parent].append((path, stat_entry))
      self._hierarchy[path] = []

  def _repr_contents(self, root: str, p: pretty.PrettyPrinter) -> None:
    with p.group(4, '', ''):
      p.group_stack[-1].want_break = True

      for path, stat_entry in self._hierarchy[root]:
        p.breakable()
        p.text(str(_StatEntryData(stat_entry)))
        self._repr_contents(path, p)

  def _repr_pretty_(self, p: pretty.PrettyPrinter, cycle: bool) -> None:
    """Print list of stat entries in IPython.

    Args:
      p: Pretty printer to pass output to.
      cycle: True, if printer detected a cycle.

    Returns:
      Nothing.
    """
    if cycle:
      raise AssertionError('Cycle in a stat entry list')

    if not self:
      p.text('No results.')
      return

    with p.group(0, '', ''):
      p.group_stack[-1].want_break = True

      for path, _ in self._hierarchy['']:
        p.breakable()
        p.text(path)
        self._repr_contents(path, p)
      p.breakable()


class BufferReferenceList(_RepresenterList):
  """Representer for a list of buffer references."""

  def _repr_pretty_(self, p: pretty.PrettyPrinter, cycle: bool) -> None:
    """Print list of buffer references in IPython.

    Args:
      p: Pretty printer to pass output to.
      cycle: True, if printer detected a cycle.

    Returns:
      Nothing.
    """
    if cycle:
      raise AssertionError('Cycle in a buffer reference list')

    if not self:
      p.text('No results.')
      return

    with p.group(0, '', ''):
      p.group_stack[-1].want_break = True

      for ref in self:
        p.breakable()
        p.text(str(_BufferReferenceData(ref)))
      p.breakable()


class ClientList(_RepresenterList):
  """Representer for a list of clients."""

  def _repr_pretty_(self, p: pretty.PrettyPrinter, cycle: bool) -> None:
    """Print list of clients in IPython.

    Args:
      p: Pretty printer to pass output to.
      cycle: True, if printer detected a cycle.

    Returns:
      Nothing.
    """
    if cycle:
      raise AssertionError('Cycle in a client list')

    if not self:
      p.text('No results.')
      return

    with p.group(0, '', ''):
      p.group_stack[-1].want_break = True

      for c in self:
        p.breakable()
        p.text(pretty.pretty(c))
      p.breakable()


class InterfaceList(_RepresenterList):
  """Representer for a list of interfaces."""

  def _repr_pretty_(self, p: pretty.PrettyPrinter, cycle: bool) -> None:
    """Print list of interfaces in IPython.

    Args:
      p: Pretty printer to pass output to.
      cycle: True, if printer detected a cycle.

    Returns:
      Nothing.
    """
    if cycle:
      raise AssertionError('Cycle in an interface list')

    if not self:
      p.text('No results.')
      return

    with p.group(0, '', ''):
      p.group_stack[-1].want_break = True

      for iface in self:
        p.breakable()
        p.text(pretty.pretty(_InterfaceData(iface)))


class ProcessList(_RepresenterList):
  """Representer for a list of processes."""

  def _repr_pretty_(self, p: pretty.PrettyPrinter, cycle: bool) -> None:
    """Print list of processes in IPython.

    Args:
      p: Pretty printer to pass output to.
      cycle: True, if printer detected a cycle.

    Returns:
      Nothing.
    """
    if cycle:
      raise AssertionError('Cycle in an process list')

    if not self:
      p.text('No results.')
      return

    header = (
        '{pid:>6s} {user:9s} {ni:>3s} {virt:>5s} {res:>5s} {s:1s} '
        '{mem:4s} {cmd}'
    )
    header = header.format(
        pid='PID',
        user='USER',
        ni='NI',
        virt='VIRT',
        res='RES',
        s='S',
        mem='MEM%',
        cmd='Command')

    with p.group(0, '', ''):
      p.group_stack[-1].want_break = True
      p.breakable()
      p.text(header[:p.max_width])

      for process in self:
        p.breakable()
        p.text(str(_ProcessData(process))[:p.max_width])
      p.breakable()


class _StatEntryData(object):
  """Class that encapsulates stat entry data displayed in IPython."""

  def __init__(self, stat_entry: jobs_pb2.StatEntry) -> None:
    self.size = stat.size(stat_entry)
    self.abs_path = os.path.normpath(stat_entry.pathspec.path)
    self.name = stat.name(stat_entry)
    self.icon = stat.icon(stat_entry)
    self.mode = stat.mode(stat_entry)

  def __str__(self) -> str:
    return '{icon} {name} ({mode} {abs_path}, {size})'.format(
        icon=self.icon,
        name=self.name,
        abs_path=self.abs_path,
        size=self.size,
        mode=self.mode)


class _BufferReferenceData(object):
  """Class that encapsulates buffer reference data displayed in IPython."""

  def __init__(self, ref: jobs_pb2.BufferReference) -> None:
    self.path = os.path.normpath(ref.pathspec.path)
    self.start = ref.offset
    self.end = ref.offset + ref.length
    self.data = ref.data

  def __str__(self) -> str:
    data_repr = repr(self.data)
    return '{path}:{start}-{end}: {data}'.format(
        path=self.path, start=self.start, end=self.end, data=data_repr)


class _InterfaceData(object):
  """Class that encapsulates interface data displayed in IPython."""

  def __init__(self, iface: jobs_pb2.Interface) -> None:
    self.name = iface.ifname
    self.addresses = iface.addresses
    self.mac = client.mac(iface.mac_address)

  def _repr_pretty_(self, p: pretty.PrettyPrinter, cycle: bool) -> None:
    """Print interface in IPython.

    Args:
      p: Pretty printer to pass output to.
      cycle: True, if printer detected a cycle.

    Returns:
      Nothing.
    """
    del cycle  # Unused.

    iface_data = '{name} (MAC: {mac}):'.format(name=self.name, mac=self.mac)

    with p.group(0, iface_data, ''):
      p.group_stack[-1].want_break = True

      with p.group(4, '', ''):
        p.group_stack[-1].want_break = True

        for addr in self.addresses:
          p.breakable()
          p.text(str(_NetworkAddressData(addr)))
      p.breakable()


class _NetworkAddressData(object):
  """Class that encapsulates network address data displayed in IPython."""

  def __init__(self, address: jobs_pb2.NetworkAddress) -> None:
    if address.address_type == jobs_pb2.NetworkAddress.INET6:
      self.type = 'inet6'
      self.address = str(ipaddress.IPv6Address(address.packed_bytes))
    else:
      self.type = 'inet'
      self.address = str(ipaddress.IPv4Address(address.packed_bytes))

  def __str__(self) -> str:
    return '{type} {address}'.format(type=self.type, address=self.address)


class _ProcessData(object):
  """Class that encapsulates process data displayed in IPython."""

  def __init__(self, process: sysinfo_pb2.Process) -> None:
    self.pid = process.pid
    self.user = process.username[:9]
    self.nice = process.nice
    self.virt = humanize.naturalsize(process.VMS_size, gnu=True, format='%.0f')
    self.res = humanize.naturalsize(process.RSS_size, gnu=True, format='%.0f')
    self.status = process.status[:1].upper()
    self.mem = '{:.1f}'.format(process.memory_percent)
    self.command = process.exe

  def __str__(self) -> str:
    data = (
        '{pid:6d} {user:9s} {ni:3d} {virt:>5s} {res:>5s} {s:1s} {mem:>4s} {cmd}'
    )

    return data.format(
        pid=self.pid,
        user=self.user,
        ni=self.nice,
        virt=str(self.virt),
        res=str(self.res),
        s=self.status,
        mem=self.mem,
        cmd=self.command)
