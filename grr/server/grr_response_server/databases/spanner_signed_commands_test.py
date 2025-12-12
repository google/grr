from absl.testing import absltest

from grr_response_server.databases import db_signed_commands_test
from grr_response_server.databases import spanner_test_lib


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabaseSignedCommandsTest(
    db_signed_commands_test.DatabaseTestSignedCommandsMixin,
    spanner_test_lib.TestCase,
):
  """Spanner signed commands tests."""


if __name__ == "__main__":
  absltest.main()
