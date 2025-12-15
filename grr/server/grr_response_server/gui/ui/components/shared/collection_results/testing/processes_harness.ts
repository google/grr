import {ComponentHarness} from '@angular/cdk/testing';

import {ProcessTreeHarness} from '../data_renderer/testing/process_tree_harness';

/** Harness for the Processes component. */
export class ProcessesHarness extends ComponentHarness {
  static hostSelector = 'processes';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly processTrees = this.locatorForAll(ProcessTreeHarness);
}
