import {MatButtonToggleGroupHarness} from '@angular/material/button-toggle/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the YaraProcessScanForm component. */
export class YaraProcessScanFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'yara-process-scan-form';

  private readonly yaraRuleFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'YARA rule'}),
  );

  private readonly filterModeToggleGroup = this.locatorFor(
    MatButtonToggleGroupHarness,
  );

  private readonly pidFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Filter comma-separated process IDs',
    }),
  );

  private readonly regexFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Filter processes matchining regex',
    }),
  );

  private readonly cmdlineFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'Filter processes matching commandline',
    }),
  );

  private readonly allFormField = this.locatorForOptional(
    MatFormFieldHarness.with({
      floatingLabelText: 'All processes, except the GRR process.',
    }),
  );

  private readonly contextWindowFormField = this.locatorFor(
    MatFormFieldHarness.with({
      floatingLabelText: 'Window size',
    }),
  );

  readonly skipReadonlyCheckboxHarness = this.locatorFor(
    MatCheckboxHarness.with({name: 'skipReadonlyRegions'}),
  );

  readonly skipExecutableCheckboxHarness = this.locatorFor(
    MatCheckboxHarness.with({name: 'skipExecutableRegions'}),
  );

  readonly skipSpecialCheckboxHarness = this.locatorFor(
    MatCheckboxHarness.with({name: 'skipSpecialRegions'}),
  );

  readonly skipSharedCheckboxHarness = this.locatorFor(
    MatCheckboxHarness.with({name: 'skipSharedRegions'}),
  );

  readonly skipMappedFilesCheckboxHarness = this.locatorFor(
    MatCheckboxHarness.with({name: 'skipMappedFiles'}),
  );

  /** Sets the YARA rule. */
  async setYaraRule(yaraRule: string): Promise<void> {
    const yaraRuleFormField = await this.yaraRuleFormField();
    const control = await yaraRuleFormField.getControl(MatInputHarness);
    await control?.setValue(yaraRule);
  }

  /** Returns the YARA rule. */
  async getYaraRule(): Promise<string> {
    const yaraRuleFormField = await this.yaraRuleFormField();
    const control = await yaraRuleFormField.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  /** Sets the filter mode. */
  async setFilterMode(
    filterMode: 'PID' | 'Name' | 'Cmdline' | 'All',
  ): Promise<void> {
    const filterModeToggleGroup = await this.filterModeToggleGroup();
    return (
      await filterModeToggleGroup.getToggles({text: filterMode})
    )[0].check();
  }

  /** Sets the PID filter. */
  async setPidFilter(pids: string): Promise<void> {
    const pidFormField = await this.pidFormField();
    if (!pidFormField) {
      throw new Error('PID form field is not found');
    }
    const pidInput = await pidFormField.getControl(MatInputHarness);
    await pidInput!.setValue(pids);
  }

  /** Returns the PID filter. */
  async getPidFilter(): Promise<string> {
    const pidFormField = await this.pidFormField();
    if (!pidFormField) {
      throw new Error('PID form field is not found');
    }
    const pidInput = await pidFormField.getControl(MatInputHarness);
    return pidInput!.getValue();
  }

  /** Sets the name filter. */
  async setNameFilter(regex: string): Promise<void> {
    const regexFormField = await this.regexFormField();
    if (!regexFormField) {
      throw new Error('Regex form field is not found');
    }
    const regexInput = await regexFormField.getControl(MatInputHarness);
    await regexInput!.setValue(regex);
  }

  /** Returns the name filter. */
  async getNameFilter(): Promise<string> {
    const regexFormField = await this.regexFormField();
    if (!regexFormField) {
      throw new Error('Regex form field is not found');
    }
    const regexInput = await regexFormField.getControl(MatInputHarness);
    return regexInput!.getValue();
  }

  /** Sets the cmdline filter. */
  async setCmdlineFilter(regex: string): Promise<void> {
    const cmdlineFormField = await this.cmdlineFormField();
    if (!cmdlineFormField) {
      throw new Error('Cmdline form field is not found');
    }
    const cmdlineInput = await cmdlineFormField.getControl(MatInputHarness);
    await cmdlineInput!.setValue(regex);
  }

  /** Returns the cmdline filter. */
  async getCmdlineFilter(): Promise<string> {
    const cmdlineFormField = await this.cmdlineFormField();
    if (!cmdlineFormField) {
      throw new Error('Cmdline form field is not found');
    }
    const cmdlineInput = await cmdlineFormField.getControl(MatInputHarness);
    return cmdlineInput!.getValue();
  }

  /** Sets the context capture window. */
  async setContextCaptureWindow(windowSize: number): Promise<void> {
    const contextWindowFormField = await this.contextWindowFormField();
    if (!contextWindowFormField) {
      throw new Error('Context window form field is not found');
    }
    const contextWindowInput =
      await contextWindowFormField.getControl(MatInputHarness);
    await contextWindowInput!.setValue(windowSize.toString());
  }

  /** Returns the context capture window. */
  async getContextCaptureWindow(): Promise<string> {
    const contextWindowFormField = await this.contextWindowFormField();
    if (!contextWindowFormField) {
      throw new Error('Context window form field is not found');
    }
    const contextWindowInput =
      await contextWindowFormField.getControl(MatInputHarness);
    return await contextWindowInput!.getValue();
  }
}
