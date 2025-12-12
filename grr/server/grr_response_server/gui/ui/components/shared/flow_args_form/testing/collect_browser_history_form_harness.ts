import {MatCheckboxHarness} from '@angular/material/checkbox/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the CollectBrowserHistoryForm component. */
export class CollectBrowserHistoryFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'collect-browser-history-form';

  readonly chromiumBasedBrowsersCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Chromium Based Browsers'}),
  );

  readonly firefoxCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Firefox'}),
  );

  readonly internetExplorerCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Internet Explorer'}),
  );

  readonly safariCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Safari'}),
  );

  readonly operaCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Opera'}),
  );
}
