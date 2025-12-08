from absl.testing import absltest

from grr_response_server.databases import db_flows_test
from grr_response_server.databases import spanner_test_lib


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabaseFlowsTest(
    db_flows_test.DatabaseTestFlowMixin, spanner_test_lib.TestCase
):
  """Spanner flow tests."""
  pass  # Test methods are defined in the base mixin class.

if __name__ == "__main__":
  absltest.main()
