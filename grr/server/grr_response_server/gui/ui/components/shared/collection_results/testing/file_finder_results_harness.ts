import {ComponentHarness} from '@angular/cdk/testing';

import {FileResultsTableHarness} from '../data_renderer/file_results_table/testing/file_results_table_harness';
import {RegistryResultsTableHarness} from '../data_renderer/testing/registry_results_table_harness';

/** Harness for the FileFinderResults component. */
export class FileFinderResultsHarness extends ComponentHarness {
  static hostSelector = 'file-finder-results';

  readonly fileResultsTable = this.locatorForOptional(FileResultsTableHarness);

  readonly registryResultsTable = this.locatorForOptional(
    RegistryResultsTableHarness,
  );
}
