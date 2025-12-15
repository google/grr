import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the LaunchBinaryForm component. */
export class LaunchBinaryFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'launch-binary-form';

  /**
   * Harness for the binary name input.
   */
  readonly binaryNameInput = this.locatorFor(MatAutocompleteHarness);

  private readonly commandLineFormField = this.locatorFor(
    MatFormFieldHarness.with({selector: '.command-line-form-field'}),
  );

  /**
   * Sets the binary name in the binary name input.
   */
  async setBinaryName(hackName: string): Promise<void> {
    const binaryNameInput = await this.binaryNameInput();
    await binaryNameInput.enterText(hackName);
  }

  /**
   * Gets the binary name in the binary name input.
   */
  async getBinaryName(): Promise<string> {
    const binaryNameInput = await this.binaryNameInput();
    return binaryNameInput.getValue();
  }

  /**
   * Sets the command line in the command line input.
   */
  async setCommandLine(commandLine: string): Promise<void> {
    const commandLineFormField = await this.commandLineFormField();
    const commandLineInput =
      await commandLineFormField.getControl(MatInputHarness);
    await commandLineInput!.setValue(commandLine);
  }

  /**
   * Gets the command line in the command line input.
   */
  async getCommandLine(): Promise<string> {
    const commandLineFormField = await this.commandLineFormField();
    const commandLineInput =
      await commandLineFormField.getControl(MatInputHarness);
    return commandLineInput!.getValue();
  }
}
