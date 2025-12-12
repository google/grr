import {TestKey} from '@angular/cdk/testing';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {
  MatChipGridHarness,
  MatChipInputHarness,
} from '@angular/material/chips/testing';
import {MatOptionHarness} from '@angular/material/core/testing';
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

  private readonly connectionStateFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Connection state'}),
  );

  private readonly connectionStateAutocomplete = this.locatorFor(
    MatAutocompleteHarness,
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

  private async getConnectionStateInputHarness(): Promise<MatChipInputHarness> {
    const connectionStateFormField = await this.connectionStateFormField();
    const control =
      await connectionStateFormField?.getControl(MatChipGridHarness);
    const input = await control?.getInput();
    if (!input) {
      throw new Error('Connection state input is not found');
    }
    return input;
  }

  async setConnectionStates(connectionState: string[]): Promise<void> {
    const input = await this.getConnectionStateInputHarness();
    await input!.focus();
    for (const state of connectionState) {
      await input!.setValue(state);
      await input!.sendSeparatorKey(TestKey.ENTER);
    }
  }

  async getConnectionState(): Promise<string[]> {
    const connectionStateFormField = await this.connectionStateFormField();
    const control =
      await connectionStateFormField?.getControl(MatChipGridHarness);
    const chips = await control?.getRows();
    return Promise.all(chips?.map((chip) => chip.getText()) ?? []);
  }

  async setConnectionStateInput(input: string): Promise<void> {
    const inputControl = await this.getConnectionStateInputHarness();
    await inputControl!.setValue(input);
  }

  async getConnectionStateInput(): Promise<string> {
    const inputControl = await this.getConnectionStateInputHarness();
    return inputControl!.getValue();
  }

  async setConnectionStateInputAndEnter(input: string): Promise<void> {
    const inputControl = await this.getConnectionStateInputHarness();
    await inputControl!.setValue(input);
    await inputControl!.sendSeparatorKey(TestKey.ENTER);
  }

  async getConnectionStateSuggestionOptions(): Promise<MatOptionHarness[]> {
    const connectionStateAutocomplete =
      await this.connectionStateAutocomplete();
    await connectionStateAutocomplete.focus();
    return connectionStateAutocomplete.getOptions();
  }

  async getConnectionStateSuggestionTexts(): Promise<string[]> {
    const connectionStateAutocomplete =
      await this.connectionStateAutocomplete();
    await connectionStateAutocomplete.focus();
    const options = await connectionStateAutocomplete.getOptions();
    return Promise.all(options.map((option) => option.getText()));
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
