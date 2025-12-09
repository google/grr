from collections.abc import Sequence

from absl.testing import absltest

from grr_response_server.databases import db_paths_test
from grr_response_server.databases import spanner_paths
from grr_response_server.databases import spanner_test_lib


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabasePathsTest(
    db_paths_test.DatabaseTestPathsMixin, spanner_test_lib.TestCase
):
  # Test methods are defined in the base mixin class.
  pass


class EncodePathComponentsTest(absltest.TestCase):

  def testEmptyComponent(self):
    with self.assertRaises(ValueError):
      spanner_paths.EncodePathComponents(("foo", "", "bar"))

  def testSlashComponent(self):
    with self.assertRaises(ValueError):
      spanner_paths.EncodePathComponents(("foo", "bar/baz", "quux"))


class EncodeDecodePathComponentsTest(absltest.TestCase):

  def testEmpty(self):
    self._testComponents(())

  def testSingle(self):
    self._testComponents(("foo",))

  def testMultiple(self):
    self._testComponents(("foo", "bar", "baz", "quux"))

  def testUnicode(self):
    self._testComponents(("zażółć", "gęślą", "jaźń"))

  def _testComponents(self, components: Sequence[str]):  # pylint: disable=invalid-name
    encoded = spanner_paths.EncodePathComponents(components)
    decoded = spanner_paths.DecodePathComponents(encoded)

    self.assertSequenceEqual(components, decoded)


if __name__ == "__main__":
  absltest.main()
