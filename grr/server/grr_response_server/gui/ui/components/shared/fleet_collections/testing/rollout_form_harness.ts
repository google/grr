import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonToggleGroupHarness} from '@angular/material/button-toggle/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {CollapsibleContainerHarness} from '../../testing/collapsible_container_harness';

/** Harness for the RolloutForm component. */
export class RolloutFormHarness extends ComponentHarness {
  static hostSelector = 'rollout-form';

  readonly clientLimitToggleGroup = this.locatorFor(
    MatButtonToggleGroupHarness.with({selector: '.client-limit-option'}),
  );

  readonly clientLimitFormField = this.locatorForOptional(
    MatFormFieldHarness.with({floatingLabelText: 'Number of clients'}),
  );

  readonly rolloutSpeedToggleGroup = this.locatorFor(
    MatButtonToggleGroupHarness.with({selector: '.rollout-speed-option'}),
  );

  readonly clientRateFormField = this.locatorForOptional(
    MatFormFieldHarness.with({floatingLabelText: 'Client rate'}),
  );

  readonly expiryTimeFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Active for'}),
  );

  // Safety limits

  readonly collapsibleContainer = this.locatorFor(
    CollapsibleContainerHarness.with({selector: '.safety-limits-container'}),
  );

  readonly crashLimitFormField = this.locatorForOptional(
    MatFormFieldHarness.with({floatingLabelText: 'Crash limit'}),
  );

  readonly avgResultsPerClientLimitFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Average results per client',
    }),
  );

  readonly avgCpuSecondsPerClientLimitFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Average CPU (per client)',
    }),
  );

  readonly avgNetworkBytesPerClientLimitFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Average network usage (per client)',
    }),
  );

  readonly cpuTimeLimitToggleGroup = this.locatorForOptional(
    MatButtonToggleGroupHarness.with({selector: '.cpu-time-limit-option'}),
  );

  readonly perClientCpuLimitFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Custom CPU time limit per client',
    }),
  );

  readonly networkBytesLimitToggleGroup = this.locatorForOptional(
    MatButtonToggleGroupHarness.with({selector: '.network-bytes-limit-option'}),
  );

  readonly perClientNetworkBytesLimitFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Custom network limit per client',
    }),
  );

  async hasClientLimitInput(): Promise<boolean> {
    return (await this.clientLimitFormField()) !== null;
  }

  async getClientLimitInput(): Promise<MatInputHarness> {
    const formField = await this.clientLimitFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async hasRolloutSpeedInput(): Promise<boolean> {
    return (await this.clientRateFormField()) !== null;
  }

  async getRolloutSpeedInput(): Promise<MatInputHarness> {
    const formField = await this.clientRateFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async getExpiryTimeInput(): Promise<MatInputHarness> {
    const formField = await this.expiryTimeFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async getCrashLimitInput(): Promise<MatInputHarness> {
    const formField = await this.crashLimitFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async getAvgResultsPerClientLimitInput(): Promise<MatInputHarness> {
    const formField = await this.avgResultsPerClientLimitFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async getAvgCpuSecondsPerClientLimitInput(): Promise<MatInputHarness> {
    const formField = await this.avgCpuSecondsPerClientLimitFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async getAvgNetworkBytesPerClientLimitInput(): Promise<MatInputHarness> {
    const formField = await this.avgNetworkBytesPerClientLimitFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async hasPerClientCpuLimitInput(): Promise<boolean> {
    return (await this.perClientCpuLimitFormField()) !== null;
  }

  async getPerClientCpuLimitInput(): Promise<MatInputHarness> {
    const formField = await this.perClientCpuLimitFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }

  async hasPerClientNetworkBytesLimitInput(): Promise<boolean> {
    return (await this.perClientNetworkBytesLimitFormField()) !== null;
  }

  async getPerClientNetworkBytesLimitInput(): Promise<MatInputHarness> {
    const formField = await this.perClientNetworkBytesLimitFormField();
    return (await formField?.getControl(MatInputHarness))!;
  }
}
