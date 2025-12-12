import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {ApproverSuggestionSubformHarness} from '../../../shared/approvals/testing/approver_suggestion_subform_harness';

/** Harness for the ClientApprovalForm component. */
export class ClientApprovalFormHarness extends ComponentHarness {
  static hostSelector = 'client-approval-form';

  private readonly reasonFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Reason for approval'}),
  );

  readonly approverSuggestionSubform = this.locatorFor(
    ApproverSuggestionSubformHarness,
  );

  private readonly ccCheckbox = this.locatorForOptional(MatCheckboxHarness);

  private readonly durationFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: /Access duration.*/}),
  );

  private readonly submitButton = this.locatorFor(
    MatButtonHarness.with({text: /Request access|Request sent/}),
  );

  async setReason(reason: string): Promise<void> {
    const reasonFormField = await this.reasonFormField();
    const control = await reasonFormField.getControl(MatInputHarness);
    await control?.blur();
    await control?.setValue(reason);
  }

  async getReason(): Promise<string> {
    const reasonFormField = await this.reasonFormField();
    const control = await reasonFormField.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  async getReasonErrors(): Promise<string[]> {
    const reasonFormField = await this.reasonFormField();
    return reasonFormField.getTextErrors();
  }

  async hasCcCheckbox(): Promise<boolean> {
    const ccCheckbox = await this.ccCheckbox();
    return !!ccCheckbox;
  }

  async checkCcCheckbox(): Promise<void> {
    const ccCheckbox = await this.ccCheckbox();
    if (!ccCheckbox) {
      throw new Error('CC checkbox is not found');
    }
    if (await ccCheckbox.isChecked()) {
      return;
    }
    await ccCheckbox?.check();
  }

  async uncheckCcCheckbox(): Promise<void> {
    const ccCheckbox = await this.ccCheckbox();
    if (!ccCheckbox) {
      throw new Error('CC checkbox is not found');
    }
    if (!(await ccCheckbox.isChecked())) {
      return;
    }
    await ccCheckbox?.uncheck();
  }

  async isCcCheckboxChecked(): Promise<boolean> {
    const ccCheckbox = await this.ccCheckbox();
    if (!ccCheckbox) {
      throw new Error('CC checkbox is not found');
    }
    return ccCheckbox.isChecked();
  }

  async setAccessDuration(duration: string) {
    const durationFormField = await this.durationFormField();
    const control = await durationFormField.getControl(MatInputHarness);
    await control?.setValue(duration);
    await control?.blur();
  }

  async getAccessDuration(): Promise<string> {
    const durationFormField = await this.durationFormField();
    const control = await durationFormField.getControl(MatInputHarness);
    return control?.getValue() ?? '';
  }

  async getAccessDurationErrors(): Promise<string[]> {
    const durationFormField = await this.durationFormField();
    return durationFormField.getTextErrors();
  }

  async isSubmitButtonDisabled(): Promise<boolean> {
    const submitButton = await this.submitButton();
    return submitButton.isDisabled();
  }

  async submit(): Promise<void> {
    const submitButton = await this.submitButton();
    await submitButton.click();
  }

  async getSubmitButtonLabel(): Promise<string> {
    const submitButton = await this.submitButton();
    return submitButton.getText();
  }
}
