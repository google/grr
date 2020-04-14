#!/usr/bin/env python
# Lint as: python3
"""Classes for handling build and repackaging of clients.

This handles invocations for the build across the supported platforms including
handling Visual Studio, pyinstaller and other packaging mechanisms.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import abc

from typing import Text

from grr_response_core import config
from grr_response_core.config import contexts


class BuildError(Exception):
  pass


REQUIRED_BUILD_YAML_KEYS = frozenset([
    "Client.build_environment",
    "Client.build_time",
    "Template.build_type",
    "Template.build_context",
    "Template.version_major",
    "Template.version_minor",
    "Template.version_revision",
    "Template.version_release",
    "Template.arch",
])


class ClientBuilder(metaclass=abc.ABCMeta):
  """A client builder is responsible for building the binary template.

  This is an abstract client builder class, used by the OS specific
  implementations. Note that client builders typically run on the target
  operating system.

  Attributes:
    context: a list corresponding to the configuration context to be
             used by this builder.
  """

  BUILDER_CONTEXT = None

  def __init__(self, context=None):
    if self.__class__.BUILDER_CONTEXT is None:
      raise ValueError("BUILDER_CONTEXT has to be defined by a subclass")

    self.context = [
        self.__class__.BUILDER_CONTEXT, contexts.CLIENT_BUILD_CONTEXT
    ] + (
        context or config.CONFIG.context[:])

  @abc.abstractmethod
  def MakeExecutableTemplate(self, output_path: Text) -> None:
    """Makes an executable template at a given location.

    The client is built in two phases. First an executable template is created
    with the client binaries contained inside a zip file. Then the installation
    package is created by appending the SFX extractor to this template and
    writing a config file into the zip file.  This technique allows the
    client build to be carried out once on the supported platform (e.g.
    windows with MSVS), but the deployable installer can be build on any
    platform which supports python.  Subclasses for each OS do the actual
    work, we just make sure the output directory is set up correctly here.

    Args:
      output_path: path where we will write the template.
    """


class ClientRepacker(metaclass=abc.ABCMeta):
  """Takes the binary template and producing an installer.

  Note that this should be runnable on all operating systems.

  Attributes:
    context: a list corresponding to the configuration context to be used by
             this repacker.
    signer: CodeSigner object to be used by this repacker (see signing.py) or
            None if no code signing will take place.
  """

  def __init__(self, context=None, signer=None):
    self.context = [contexts.CLIENT_BUILD_CONTEXT] + (
        context or config.CONFIG.context[:])
    self.signer = signer

  @abc.abstractmethod
  def MakeDeployableBinary(self, template_path: Text, output_path: Text):
    """Use the template to create a customized installer."""
