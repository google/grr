#!/usr/bin/env python
"""This module contains windows specific client code."""



# These need to register plugins so, pylint: disable=W0611
from grr.client.windows import installers
from grr.client.windows import regconfig
