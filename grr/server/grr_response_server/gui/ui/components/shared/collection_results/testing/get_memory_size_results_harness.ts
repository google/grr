import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the GetMemorySizeResults component. */
export class GetMemorySizeResultsHarness extends ComponentHarness {
  static hostSelector = 'get-memory-size-results';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly memorySize = this.locatorForAll('.memory-size');
}
