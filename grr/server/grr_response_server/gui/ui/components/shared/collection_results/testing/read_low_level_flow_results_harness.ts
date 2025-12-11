import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the ReadLowLevelFlowResults component. */
export class ReadLowLevelFlowResultsHarness extends ComponentHarness {
  static hostSelector = 'read-low-level-flow-results';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly listedFiles = this.locatorForAll('li');
}
