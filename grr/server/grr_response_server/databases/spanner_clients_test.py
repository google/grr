from absl.testing import absltest

from grr_response_server.databases import db
from grr_response_server.databases import db_clients_test
from grr_response_server.databases import db_test_utils
from grr_response_server.databases import spanner_test_lib


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabaseClientsTest(
    db_clients_test.DatabaseTestClientsMixin, spanner_test_lib.TestCase
):
  # Test methods are defined in the base mixin class.

  def testLabelWriteToUnknownUser(self):
    client_id = db_test_utils.InitializeClient(self.db)

    with self.assertRaises(db.UnknownGRRUserError) as ctx:
      self.db.AddClientLabels(client_id, owner="foo", labels=["bar", "baz"])

    self.assertIsInstance(ctx.exception, db.UnknownGRRUserError)
    self.assertEqual(ctx.exception.username, "foo")


if __name__ == "__main__":
  absltest.main()
