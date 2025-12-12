import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the StartupInfoDetails component. */
export class StartupInfoDetailsHarness extends ComponentHarness {
  static hostSelector = 'startup-info-details';

  readonly table = this.locatorFor('table');
}
