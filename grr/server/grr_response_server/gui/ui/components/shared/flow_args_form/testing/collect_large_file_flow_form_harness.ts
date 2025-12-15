import {MatInputHarness} from '@angular/material/input/testing';
import {MatRadioGroupHarness} from '@angular/material/radio/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the CollectLargeFileFlowForm component. */
export class CollectLargeFileFlowFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'collect-large-file-flow-form';

  private readonly pathInput = this.locatorFor(
    MatInputHarness.with({selector: 'textarea[name=path]'}),
  );
  private readonly pathTypeRadioGroup = this.locatorFor(MatRadioGroupHarness);

  private readonly signedUrlInput = this.locatorFor(
    MatInputHarness.with({selector: 'textarea[name=signed_url]'}),
  );

  private readonly inputError = this.locatorForOptional('mat-error');

  /** Sets the value of the paths input. */
  async setPathInput(value: string) {
    const input = await this.pathInput();
    await input.setValue(value);
  }

  /** Gets the value of the paths input. */
  async getPathInput(): Promise<string> {
    const input = await this.pathInput();
    return input.getValue();
  }

  /** Sets the value of the signed URL input. */
  async setSignedUrlInput(value: string) {
    const input = await this.signedUrlInput();
    await input.setValue(value);
  }

  /** Gets the value of the signed URL input. */
  async getSignedUrlInput(): Promise<string> {
    const input = await this.signedUrlInput();
    return input.getValue();
  }

  /** Checks whether the input has an error. */
  async hasInputError(): Promise<boolean> {
    return (await this.inputError()) !== null;
  }

  /** Gets the error message of the input. */
  async getInputError(): Promise<string | null> {
    const error = await this.inputError();
    return error?.text() ?? null;
  }

  /** Gets the text of the active path type. */
  async getSelectedPathTypeText(): Promise<string | undefined> {
    const pathTypeRadioGroup = await this.pathTypeRadioGroup();
    const checkedRadioButton =
      await pathTypeRadioGroup?.getCheckedRadioButton();
    return checkedRadioButton?.getLabelText();
  }

  /** Sets the active path type to the one with the given text. */
  async setPathType(radioText: string) {
    const pathTypeRadioGroup = await this.pathTypeRadioGroup();
    await pathTypeRadioGroup.checkRadioButton({label: radioText});
  }
}
