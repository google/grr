import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the CloudInstanceDetails component. */
export class CloudInstanceDetailsHarness extends ComponentHarness {
  static hostSelector = 'cloud-instance-details';

  readonly table = this.locatorFor('table');
}
