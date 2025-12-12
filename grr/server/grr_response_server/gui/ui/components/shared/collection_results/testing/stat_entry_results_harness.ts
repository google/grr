import {ComponentHarness} from '@angular/cdk/testing';

import {CollapsibleContainerHarness} from '../../testing/collapsible_container_harness';
import {FileResultsTableHarness} from '../data_renderer/file_results_table/testing/file_results_table_harness';
import {RegistryResultsTableHarness} from '../data_renderer/testing/registry_results_table_harness';

/** Harness for the StatEntryResults component. */
export class StatEntryResultsHarness extends ComponentHarness {
  static hostSelector = 'stat-entry-results';

  readonly fileResultsTables = this.locatorForAll(FileResultsTableHarness);
  readonly registryResultsTables = this.locatorForAll(
    RegistryResultsTableHarness,
  );

  readonly collapsibleContainers = this.locatorForAll(
    CollapsibleContainerHarness,
  );
}
