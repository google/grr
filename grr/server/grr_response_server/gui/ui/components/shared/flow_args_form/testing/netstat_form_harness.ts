import {MatCheckboxHarness} from '@angular/material/checkbox/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the NetstatForm component. */
export class NetstatFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'netstat-form';

  private readonly listeningOnlyCheckboxHarness =
    this.locatorFor(MatCheckboxHarness);

  /** Toggles the listening only checkbox. */
  async toggleListeningOnly(): Promise<void> {
    const listeningOnlyCheckboxHarness =
      await this.listeningOnlyCheckboxHarness();
    await listeningOnlyCheckboxHarness.check();
  }

  /** Returns the listening only checkbox state. */
  async getListeningOnly(): Promise<boolean> {
    const listeningOnlyCheckboxHarness =
      await this.listeningOnlyCheckboxHarness();
    return listeningOnlyCheckboxHarness.isChecked();
  }
}
