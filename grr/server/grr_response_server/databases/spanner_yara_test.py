from absl.testing import absltest

from grr_response_server.databases import db_yara_test_lib
from grr_response_server.databases import spanner_test_lib


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabaseYaraTest(
    db_yara_test_lib.DatabaseTestYaraMixin, spanner_test_lib.TestCase
):
  # Test methods are defined in the base mixin class.
  pass


if __name__ == "__main__":
  absltest.main()
