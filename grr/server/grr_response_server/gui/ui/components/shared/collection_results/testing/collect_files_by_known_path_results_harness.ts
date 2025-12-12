import {ComponentHarness} from '@angular/cdk/testing';

import {FileResultsTableHarness} from '../data_renderer/file_results_table/testing/file_results_table_harness';

/** Harness for the CollectFilesByKnownPathResults component. */
export class CollectFilesByKnownPathResultsHarness extends ComponentHarness {
  static hostSelector = 'collect-files-by-known-path-results';

  readonly fileResultsTables = this.locatorFor(FileResultsTableHarness);
}
