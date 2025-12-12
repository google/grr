import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the HardwareInfoDetails component. */
export class HardwareInfoDetailsHarness extends ComponentHarness {
  static hostSelector = 'hardware-info-details';

  readonly table = this.locatorFor('table');
}
