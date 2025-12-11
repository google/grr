import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ExecutePythonHackForm component. */
export class ExecutePythonHackFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'execute-python-hack-form';

  /**
   * Harness for the hack name input.
   */
  readonly hackNameInput = this.locatorFor(MatAutocompleteHarness);

  private readonly addArgumentButton = this.locatorFor(
    MatButtonHarness.with({text: 'Add argument'}),
  );

  private readonly argsKeyFormFields = this.locatorForAll(
    MatFormFieldHarness.with({selector: '.key-input'}),
  );

  private readonly argsValueFormFields = this.locatorForAll(
    MatFormFieldHarness.with({selector: '.value-input'}),
  );

  /**
   * Sets the hack name in the hack name input.
   */
  async setHackName(hackName: string): Promise<void> {
    const hackNameInput = await this.hackNameInput();
    await hackNameInput.enterText(hackName);
  }

  /**
   * Adds a new key-value argument to the form.
   */
  async addKeyValueArgument(): Promise<void> {
    const addArgumentButton = await this.addArgumentButton();
    await addArgumentButton.click();
  }

  /**
   * Removes a key-value argument from the form.
   */
  async removeKeyValueArgument(index: number): Promise<void> {
    const argFormFields = await this.argsValueFormFields();

    const removeButton =
      await argFormFields[index].getControl(MatButtonHarness);
    await removeButton!.click();
  }

  /**
   * Sets the key-value argument in the form.
   */
  async setKeyValueArgument(
    index: number,
    key: string,
    value: string,
  ): Promise<void> {
    const keyFormFields = await this.argsKeyFormFields();
    const valueFormFields = await this.argsValueFormFields();
    if (index >= keyFormFields.length || index >= valueFormFields.length) {
      throw new Error(
        `Index ${index} is out of bounds for keyFormFields (${keyFormFields.length}) and valueFormFields (${valueFormFields.length})`,
      );
    }
    const keyInput = await keyFormFields[index].getControl(MatInputHarness);
    await keyInput!.setValue(key);
    const valueInput = await valueFormFields[index].getControl(MatInputHarness);
    await valueInput!.setValue(value);
  }

  /**
   * Gets the key-value argument in the form.
   */
  async getKeyValueArgument(index: number): Promise<string[]> {
    const keyFormFields = await this.argsKeyFormFields();
    const valueFormFields = await this.argsValueFormFields();
    if (index >= keyFormFields.length || index >= valueFormFields.length) {
      throw new Error(
        `Index ${index} is out of bounds for keyFormFields (${keyFormFields.length}) and valueFormFields (${valueFormFields.length})`,
      );
    }
    const keyInput = await keyFormFields[index].getControl(MatInputHarness);
    const valueInput = await valueFormFields[index].getControl(MatInputHarness);
    return [await keyInput!.getValue(), await valueInput!.getValue()];
  }

  /**
   * Gets the number of key-value arguments in the form.
   */
  async getNumberOfKeyValueArguments(): Promise<number> {
    const keyFormFields = await this.argsKeyFormFields();
    return keyFormFields.length;
  }
}
