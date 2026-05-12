import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the CollectDistroInfoResults component. */
export class CollectDistroInfoResultsHarness extends ComponentHarness {
  static hostSelector = 'collect-distro-info-results';

  readonly tables = this.locatorForAll('table');
}
