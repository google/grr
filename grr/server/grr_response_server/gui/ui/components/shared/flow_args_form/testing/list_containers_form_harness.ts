import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ListContainersForm component. */
export class ListContainersFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'list-containers-form';

  readonly inspectHostrootCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Inspect hostroot'}),
  );
}
