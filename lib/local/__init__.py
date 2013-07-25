#!/usr/bin/env python
"""This directory contains local site-specific implementations."""


import logging
from grr.lib import config_lib
from grr.lib import log as lib_log


def ConfigInit():
  config_lib.ConfigLibInit()


def ServerLogInit():
  lib_log.LogInit()
  lib_log.AppLogInit()


def ClientLogInit():
  lib_log.LogInit()


