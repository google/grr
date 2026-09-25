import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ListProcessesForm component. */
export class ListProcessesFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'list-processes-form';

  private readonly filenameRegexFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Executable path regex'}),
  );

  private readonly pidsFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'PIDs'}),
  );

  private readonly fetchBinariesCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Collect process executables'}),
  );

  async setFilenameRegex(pathRegex: string): Promise<void> {
    const filenameRegexFormField = await this.filenameRegexFormField();
    const control = await filenameRegexFormField.getControl(MatInputHarness);
    await control?.setValue(pathRegex);
  }

  async getFilenameRegex(): Promise<string> {
    const filenameRegexFormField = await this.filenameRegexFormField();
    const control = await filenameRegexFormField.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  async setPids(pids: string): Promise<void> {
    const pidsFormField = await this.pidsFormField();
    const control = await pidsFormField.getControl(MatInputHarness);
    await control?.setValue(pids);
    await control?.blur();
  }

  async getPids(): Promise<string> {
    const pidsFormField = await this.pidsFormField();
    const control = await pidsFormField.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  async getPidsErrors(): Promise<string[]> {
    const pidsFormField = await this.pidsFormField();
    return pidsFormField.getTextErrors();
  }

  async setFetchBinariesCheckbox(checked: boolean): Promise<void> {
    const fetchBinariesCheckbox = await this.fetchBinariesCheckbox();
    if ((await fetchBinariesCheckbox.isChecked()) === checked) {
      return;
    }
    await fetchBinariesCheckbox.toggle();
  }

  async getFetchBinariesCheckbox(): Promise<boolean> {
    const fetchBinariesCheckbox = await this.fetchBinariesCheckbox();
    return fetchBinariesCheckbox.isChecked();
  }
}
