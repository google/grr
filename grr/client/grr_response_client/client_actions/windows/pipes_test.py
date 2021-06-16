#!/usr/bin/env python
import contextlib
import os
import platform
from typing import Iterator
from typing import Optional
import uuid

from absl.testing import absltest

from grr_response_client.client_actions.windows import pipes

if platform.system() == "Windows":
  # pylint: disable=g-import-not-at-top
  # pytype: disable=import-error
  import win32pipe
  # pytype: enable=import-error
  # pylint: enable=g-import-not-at-top


@absltest.skipUnless(
    platform.system() == "Windows",
    reason="Windows-only action.",
)
class ListNamedPipesTest(absltest.TestCase):

  def testSinglePipe(self) -> None:
    pipe_name = str(uuid.uuid4())
    pipe_spec = NamedPipeSpec(pipe_name)

    with pipe_spec.Create():
      results = list(pipes.ListNamedPipes())

    names = set(result.name for result in results)
    self.assertIn(pipe_name, names)

  def testMultiplePipes(self) -> None:
    pipe_name_1 = str(uuid.uuid4())
    pipe_name_2 = str(uuid.uuid4())

    pipe_spec_1 = NamedPipeSpec(pipe_name_1)
    pipe_spec_2 = NamedPipeSpec(pipe_name_2)

    with pipe_spec_1.Create():
      with pipe_spec_2.Create():
        results = list(pipes.ListNamedPipes())

    names = set(result.name for result in results)
    self.assertIn(pipe_name_1, names)
    self.assertIn(pipe_name_2, names)

  def testPipeTypeByte(self) -> None:
    self._testPipeType(win32pipe.PIPE_TYPE_BYTE)

  def testPipeTypeMessage(self) -> None:
    self._testPipeType(win32pipe.PIPE_TYPE_MESSAGE)

  def _testPipeType(self, pipe_type: int) -> None:  # pylint: disable=invalid-name
    pipe_name = str(uuid.uuid4())

    pipe_spec = NamedPipeSpec(pipe_name)
    pipe_spec.pipe_mode = pipe_type

    with pipe_spec.Create():
      results = list(pipes.ListNamedPipes())

    results_by_name = {result.name: result for result in results}
    result = results_by_name[pipe_name]

    self.assertEqual(result.flags & pipe_type, pipe_type)

  def testMaxInstanceCountLimited(self) -> None:
    self._testMaxInstanceCount(42)

  def testMaxInstanceCountUnlimited(self) -> None:
    self._testMaxInstanceCount(win32pipe.PIPE_UNLIMITED_INSTANCES)

  def _testMaxInstanceCount(self, count: int) -> None:  # pylint: disable=invalid-name
    pipe_name = str(uuid.uuid4())

    pipe_spec = NamedPipeSpec(pipe_name)
    pipe_spec.max_instance_count = count

    with pipe_spec.Create():

      results = list(pipes.ListNamedPipes())

    results_by_name = {result.name: result for result in results}
    result = results_by_name[pipe_name]

    self.assertEqual(result.max_instance_count, count)

  def testCurInstanceCount(self) -> None:
    pipe_name = str(uuid.uuid4())
    pipe_spec = NamedPipeSpec(pipe_name)

    with pipe_spec.Create():
      with pipe_spec.Create():
        with pipe_spec.Create():
          results = list(pipes.ListNamedPipes())

    results_by_name = {result.name: result for result in results}
    result = results_by_name[pipe_name]

    self.assertEqual(result.cur_instance_count, 3)

  def testBufferSize(self) -> None:
    pipe_name = str(uuid.uuid4())

    pipe_spec = NamedPipeSpec(pipe_name)
    pipe_spec.in_buffer_size = 42
    pipe_spec.out_buffer_size = 108

    with pipe_spec.Create():
      results = list(pipes.ListNamedPipes())

    results_by_name = {result.name: result for result in results}
    result = results_by_name[pipe_name]

    self.assertEqual(result.in_buffer_size, 42)
    self.assertEqual(result.out_buffer_size, 108)

  def testPid(self) -> None:
    pipe_name = str(uuid.uuid4())
    pipe_spec = NamedPipeSpec(pipe_name)

    with pipe_spec.Create():
      results = list(pipes.ListNamedPipes())

    results_by_name = {result.name: result for result in results}
    result = results_by_name[pipe_name]

    self.assertEqual(result.server_pid, os.getpid())
    self.assertEqual(result.client_pid, os.getpid())


class NamedPipeSpec:
  """A class with named pipe specification."""
  name: str
  open_mode: Optional[int] = None
  pipe_mode: Optional[int] = None
  max_instance_count: Optional[int] = None
  in_buffer_size: int = 0
  out_buffer_size: int = 0
  default_timeout_millis: int = 0

  def __init__(self, name: str) -> None:
    self.name = name

  @contextlib.contextmanager
  def Create(self) -> Iterator[None]:
    """Creates a named pipe context conforming to the specification."""
    if self.max_instance_count is not None:
      max_instance_count = self.max_instance_count
    else:
      max_instance_count = win32pipe.PIPE_UNLIMITED_INSTANCES

    if self.open_mode is not None:
      open_mode = self.open_mode
    else:
      open_mode = win32pipe.PIPE_ACCESS_DUPLEX

    if self.pipe_mode is not None:
      pipe_mode = self.pipe_mode
    else:
      pipe_mode = 0

    handle = win32pipe.CreateNamedPipe(
        f"\\\\.\\pipe\\{self.name}",
        open_mode,
        pipe_mode,
        max_instance_count,
        self.in_buffer_size,
        self.out_buffer_size,
        self.default_timeout_millis,
        None,
    )

    with contextlib.closing(handle):
      yield


if __name__ == "__main__":
  absltest.main()
