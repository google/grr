import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the CollectDistroInfoResults component. */
export class CollectDistroInfoResultsHarness extends ComponentHarness {
  static hostSelector = 'collect-distro-info-results';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly tables = this.locatorForAll('table');
}
