#!/usr/bin/env python
import os
from typing import Optional, Tuple
from unittest import mock

from absl.testing import absltest
from absl.testing import flagsaver

from grr_response_client import client_utils
from grr_response_client import vfs
from grr_response_core import config
from grr_response_core.lib import config_lib
from grr_response_core.lib.rdfvalues import paths as rdf_paths
from grr_response_core.lib.rdfvalues import structs as rdf_structs
from grr_response_core.lib.util import temp


class VfsImplementationTypeTest(absltest.TestCase):
  """Tests that the `PathSpec.implementation_type` is correctly propagated."""

  def _CreateNestedPathSpec(
      self,
      path: str,
      implementation_type: Optional[rdf_structs.EnumNamedValue],
      path_options: Optional[rdf_structs.EnumNamedValue] = None
  ) -> rdf_paths.PathSpec:
    ntfs_img_path = os.path.join(config.CONFIG["Test.data_dir"], "ntfs.img")

    return rdf_paths.PathSpec(
        implementation_type=implementation_type,
        path=ntfs_img_path,
        pathtype=rdf_paths.PathSpec.PathType.OS,
        path_options=rdf_paths.PathSpec.Options.CASE_LITERAL,
        nested_path=rdf_paths.PathSpec(
            path=path,
            pathtype=rdf_paths.PathSpec.PathType.NTFS,
            path_options=path_options,
        ))

  def _CheckHasImplementationType(
      self, pathspec: rdf_paths.PathSpec,
      implementation_type: rdf_paths.PathSpec.ImplementationType) -> None:
    if implementation_type is None:
      self.assertFalse(pathspec.HasField("implementation_type"))
    else:
      self.assertEqual(pathspec.implementation_type, implementation_type)
    for i, component in enumerate(pathspec):
      if i > 0:
        self.assertFalse(component.HasField("implementation_type"))

  def _OpenAndCheckImplementationType(
      self, pathspec: rdf_paths.PathSpec,
      implementation_type: rdf_paths.PathSpec.ImplementationType) -> None:
    with vfs.VFSOpen(pathspec) as f:
      self._CheckHasImplementationType(f.pathspec, implementation_type)
      self._CheckHasImplementationType(f.Stat().pathspec, implementation_type)
      for child in f.ListFiles():
        self._CheckHasImplementationType(child.pathspec, implementation_type)

  def _MockGetRawDevice(self, path: str) -> Tuple[rdf_paths.PathSpec, str]:
    return (self._CreateNestedPathSpec(path, None), path)

  def testVfsOpen_default_nestedPath(self):

    pathspec = self._CreateNestedPathSpec("/", None)
    self._OpenAndCheckImplementationType(pathspec, None)

  def testVfsOpen_direct_nestedPath(self):
    pathspec = self._CreateNestedPathSpec(
        "/", rdf_paths.PathSpec.ImplementationType.DIRECT)
    self._OpenAndCheckImplementationType(
        pathspec, rdf_paths.PathSpec.ImplementationType.DIRECT)

  def testVfsOpen_direct_caseLiteral_nestedPath(self):
    pathspec = self._CreateNestedPathSpec(
        "/", rdf_paths.PathSpec.ImplementationType.DIRECT,
        rdf_paths.PathSpec.Options.CASE_LITERAL)
    self._OpenAndCheckImplementationType(
        pathspec, rdf_paths.PathSpec.ImplementationType.DIRECT)

  def testVfsOpen_sandbox_nestedPath(self):
    pathspec = self._CreateNestedPathSpec(
        "/", rdf_paths.PathSpec.ImplementationType.SANDBOX)
    self._OpenAndCheckImplementationType(
        pathspec, rdf_paths.PathSpec.ImplementationType.SANDBOX)

  def testVfsOpen_default_rawPath(self):
    with mock.patch.object(
        client_utils, "GetRawDevice", new=self._MockGetRawDevice):
      pathspec = rdf_paths.PathSpec(
          path="/", pathtype=rdf_paths.PathSpec.PathType.NTFS)
      self._OpenAndCheckImplementationType(pathspec, None)

  def testVfsOpen_direct_rawPath(self):
    with mock.patch.object(
        client_utils, "GetRawDevice", new=self._MockGetRawDevice):
      pathspec = rdf_paths.PathSpec(
          path="/",
          pathtype=rdf_paths.PathSpec.PathType.NTFS,
          implementation_type=rdf_paths.PathSpec.ImplementationType.DIRECT)
      self._OpenAndCheckImplementationType(
          pathspec, rdf_paths.PathSpec.ImplementationType.DIRECT)

  def testVfsOpen_sandbox_rawPath(self):
    with mock.patch.object(
        client_utils, "GetRawDevice", new=self._MockGetRawDevice):
      pathspec = rdf_paths.PathSpec(
          path="/",
          pathtype=rdf_paths.PathSpec.PathType.NTFS,
          implementation_type=rdf_paths.PathSpec.ImplementationType.SANDBOX)
      self._OpenAndCheckImplementationType(
          pathspec, rdf_paths.PathSpec.ImplementationType.SANDBOX)


def setUpModule() -> None:
  with temp.AutoTempFilePath(suffix=".yaml") as dummy_config_path:
    with flagsaver.flagsaver(config=dummy_config_path):
      config_lib.ParseConfigCommandLine()


if __name__ == "__main__":
  absltest.main()
