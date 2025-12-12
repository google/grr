import {ComponentHarness} from '@angular/cdk/testing';

import {FileResultsTableHarness} from '../data_renderer/file_results_table/testing/file_results_table_harness';

/** Harness for the CollectMultipleFilesResults component. */
export class CollectMultipleFilesResultsHarness extends ComponentHarness {
  static hostSelector = 'collect-multiple-files-results';

  readonly fileResultsTables = this.locatorForOptional(FileResultsTableHarness);
}
