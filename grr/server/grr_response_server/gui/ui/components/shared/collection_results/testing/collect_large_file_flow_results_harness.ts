import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the CollectLargeFileFlowResults component. */
export class CollectLargeFileFlowResultsHarness extends ComponentHarness {
  static hostSelector = 'collect-large-file-flow-results';

  readonly tables = this.locatorForAll('table');
}
