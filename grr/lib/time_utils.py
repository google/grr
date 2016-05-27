#!/usr/bin/env python
"""This file contains various utilities for datetime handling."""



import calendar
import datetime
import re
import time

# Special Windows value for 'the beginning of time'
NULL_FILETIME = datetime.datetime(1601, 1, 1, 0, 0, 0)

# Regex for times in windows wmi converted format 20080726084622.375000+120
TIME_WMI_RE = re.compile(r"(?P<date>\d{14})\."  # date then .
                         r"(?P<subsecond>\d{6})[+-]"  # secs then + or -
                         r"(?P<tzoffset>\d{3})")  # minute timezone offset


def DatetimeToWmiTime(dt):
  """Take a datetime tuple and return it as yyyymmddHHMMSS.mmmmmm+UUU string.

  Args:
    dt: A datetime object.

  Returns:
    A string in CMI_DATETIME format.

  http://www.dmtf.org/sites/default/files/standards/documents/DSP0004_2.5.0.pdf
  """
  td = dt.utcoffset()
  if td:
    offset = (td.seconds + (td.days * 60 * 60 * 24)) / 60
    if offset >= 0:
      str_offset = "+%03d" % offset
    else:
      str_offset = "%03d" % offset
  else:
    str_offset = "+000"
  return u"%04d%02d%02d%02d%02d%02d.%06d%s" % (dt.year, dt.month, dt.day,
                                               dt.hour, dt.minute, dt.second,
                                               dt.microsecond, str_offset)


def WmiTimeToEpoch(cimdatetime_str):
  """Convert a CIM_DATETIME string to microseconds since epoch.

  Args:
    cimdatetime_str: A string in WMI format

  Returns:
    Microseconds since epoch as int or 0 on failure.

  http://www.dmtf.org/sites/default/files/standards/documents/DSP0004_2.5.0.pdf
  """
  re_match = TIME_WMI_RE.match(cimdatetime_str)
  try:
    t_dict = re_match.groupdict()
    flt_time = time.strptime(t_dict["date"], "%Y%m%d%H%M%S")
    epoch_time = int(calendar.timegm(flt_time)) * 1000000
    # Note that the tzoffset value is ignored, CIM_DATETIME stores in UTC
    epoch_time += int(t_dict["subsecond"])
    return epoch_time
  except (KeyError, AttributeError):
    return 0


def WinFileTimeToDateTime(filetime):
  """Take a Windows FILETIME as integer and convert to DateTime."""
  return NULL_FILETIME + datetime.timedelta(microseconds=filetime / 10)


def AmericanDateToEpoch(date_str):
  """Take a US format date and return epoch. Used for some broken WMI calls."""
  try:
    epoch = time.strptime(date_str, "%m/%d/%Y")
    return int(calendar.timegm(epoch)) * 1000000
  except ValueError:
    return 0
