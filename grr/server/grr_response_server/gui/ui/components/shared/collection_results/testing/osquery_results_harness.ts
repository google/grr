import {ComponentHarness} from '@angular/cdk/testing';

import {OsqueryTableHarness} from '../data_renderer/testing/osquery_table_harness';

/** Harness for the OsqueryResults component. */
export class OsqueryResultsHarness extends ComponentHarness {
  static hostSelector = 'osquery-results';

  readonly osqueryTables = this.locatorForAll(OsqueryTableHarness);
}
