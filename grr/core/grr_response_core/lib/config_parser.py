#!/usr/bin/env python
"""GRR config parsing code."""

import abc
import configparser
import errno
import io
import logging
import os
from typing import Any, BinaryIO

import yaml


class Error(Exception):
  pass


class SaveDataError(Error):
  """Raised when config data can't be saved."""


class SaveDataPathNotSpecifiedError(SaveDataError):
  """Raised on save, if config path is not specified."""


class ReadDataError(Error):
  """Raised when config data can't be read."""


class ReadDataPathNotSpecifiedError(ReadDataError):
  """Raised on read, if config path is not specified."""


class ReadDataPermissionError(ReadDataError):
  """Raised when config is present but can't be accessed."""


class GRRConfigParser(metaclass=abc.ABCMeta):
  """The base class for all GRR configuration parsers."""

  def __init__(self, config_path: str) -> None:
    self._config_path = config_path

  def __str__(self) -> str:
    return '<%s config_path="%s">' % (
        self.__class__.__name__,
        self._config_path,
    )

  @property
  def config_path(self) -> str:
    return self._config_path

  @abc.abstractmethod
  def Copy(self) -> "GRRConfigParser":
    raise NotImplementedError()

  @abc.abstractmethod
  def SaveData(self, raw_data: dict[str, Any]) -> None:
    raise NotImplementedError()

  @abc.abstractmethod
  def ReadData(self) -> dict[str, Any]:
    """Convert the file to a more suitable data structure.

    Returns:
    The standard data format from this method is for example:

    {
     name: default_value;
     name2: default_value2;

     "Context1": {
         name: value,
         name2: value,

         "Nested Context" : {
           name: value;
         };
      },
     "Context2": {
         name: value,
      }
    }

    i.e. raw_data is an OrderedDict() with keys representing parameter names
    and values representing values. Contexts are represented by nested
    OrderedDict() structures with similar format.

    Note that support for contexts is optional and depends on the config file
    format. If contexts are not supported, a flat OrderedDict() is returned.
    """
    raise NotImplementedError()


class GRRConfigFileParser(GRRConfigParser):
  """Base class for file-based parsers."""

  @abc.abstractmethod
  def RawDataToBytes(self, raw_data: dict[str, Any]) -> bytes:
    raise NotImplementedError()

  @abc.abstractmethod
  def RawDataFromBytes(self, b: bytes) -> dict[str, Any]:
    raise NotImplementedError()

  def SaveDataToFD(
      self, raw_data: dict[str, Any], fd: io.BufferedWriter
  ) -> None:
    fd.write(self.RawDataToBytes(raw_data))

  def ReadDataFromFD(self, fd: BinaryIO) -> dict[str, Any]:
    return self.RawDataFromBytes(fd.read())

  def SaveData(self, raw_data: dict[str, Any]) -> None:
    """Store the raw data as our configuration."""
    if not self.config_path:
      raise SaveDataPathNotSpecifiedError("Parser's config_path is empty.")

    logging.info("Writing back configuration to file %s", self.config_path)
    # Ensure intermediate directories exist
    try:
      os.makedirs(os.path.dirname(self.config_path))
    except OSError:
      pass

    try:
      # We can not use the standard open() call because we need to
      # enforce restrictive file permissions on the created file.
      mode = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
      fd = os.open(self.config_path, mode, 0o600)
      with os.fdopen(fd, "wb") as config_file:
        config_file.write(self.RawDataToBytes(raw_data))

    except OSError as e:
      logging.exception(
          "Unable to write config file %s: %s.", self.config_path, e
      )
      raise SaveDataError(
          f"Unable to write config file {self.config_path}: {e}."
      ) from e

  def ReadData(self) -> dict[str, Any]:
    if not self.config_path:
      raise ReadDataPathNotSpecifiedError("Parser's config_path is empty.")

    try:
      # TODO(user): a normal "open" would do, but we have a test
      # in config_lib_test.py that relies on mocking io.open.
      with io.open(self.config_path, "rb") as fd:
        return self.ReadDataFromFD(fd)
    except OSError as e:
      if e.errno == errno.EACCES:
        # Specifically catch access denied errors, this usually indicates the
        # user wanted to read the file, and it existed, but they lacked the
        # permissions.
        raise ReadDataPermissionError(e) from e

      return dict()

  def Copy(self) -> "GRRConfigFileParser":
    return self.__class__(self._config_path)  # pytype: disable=not-instantiable


class IniConfigFileParser(GRRConfigFileParser):
  """A parser for ini style config files."""

  def RawDataToBytes(self, raw_data: dict[str, Any]) -> bytes:
    parser = self._Parser()

    for key, value in raw_data.items():
      parser.set("", key, value=value)

    sio = io.StringIO()
    parser.write(sio)
    return sio.getvalue().encode("utf-8")

  def RawDataFromBytes(self, b: bytes) -> dict[str, Any]:
    parser = self._Parser()
    parser.read_file(b.decode("utf-8").splitlines())

    raw_data = dict()
    for section in parser.sections():
      for key, value in parser.items(section):
        raw_data[".".join([section, key])] = value

    return raw_data

  def _Parser(self):
    parser = configparser.RawConfigParser()
    parser.optionxform = str
    return parser


class YamlConfigFileParser(GRRConfigFileParser):
  """A parser for yaml style config files."""

  def RawDataToBytes(self, raw_data: dict[str, Any]) -> bytes:
    return yaml.safe_dump(raw_data).encode("utf-8")

  def RawDataFromBytes(self, b: bytes) -> dict[str, Any]:
    return yaml.safe_load(b.decode("utf-8")) or dict()


class FileParserDataWrapper(GRRConfigParser):
  """Wrapper that makes GRRConfigFileParser read data from predefined bytes."""

  def __init__(self, data: bytes, parser: GRRConfigFileParser):
    # Use an empty config_path.
    super().__init__("")
    self._data = data
    self._parser = parser

  def SaveData(self, raw_data: dict[str, Any]) -> None:
    raise SaveDataError("File parser initialized from bytes can't save data.")

  def ReadData(self) -> dict[str, Any]:
    return self._parser.RawDataFromBytes(self._data)

  def Copy(self) -> "FileParserDataWrapper":
    return self.__class__(self._data, self._parser)


_ADDITIONAL_PARSERS: dict[str, type[GRRConfigParser]] = {}


def RegisterParserClass(scheme: str, parser_cls: type[GRRConfigParser]) -> None:
  _ADDITIONAL_PARSERS[scheme] = parser_cls


def _GetParserClassFromPath(path: str) -> type[GRRConfigParser]:
  """Returns the appropriate parser class from the path."""
  # Find the configuration parser.
  path_scheme = path.split("://")[0]
  for scheme, parser_cls in _ADDITIONAL_PARSERS.items():
    if scheme == path_scheme:
      return parser_cls

  # Handle the filename.
  extension = os.path.splitext(path)[1]
  if extension in [".yaml", ".yml"]:
    return YamlConfigFileParser

  return IniConfigFileParser


def GetParserFromPath(path: str) -> GRRConfigParser:
  """Returns the appropriate parser class from the path."""
  cls = _GetParserClassFromPath(path)
  return cls(path)  # pytype: disable=not-instantiable
