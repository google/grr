import {MatButtonHarness} from '@angular/material/button/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatRadioGroupHarness} from '@angular/material/radio/testing';
import {FormErrorsHarness} from '../../form/testing/form_validation_harness';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the CollectFilesByKnownPathForm component. */
export class CollectFilesByKnownPathFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'collect-files-by-known-path-form';

  private readonly pathsInput = this.locatorFor(
    MatInputHarness.with({selector: 'textarea[name=paths]'}),
  );

  /** Harness for the input error. */
  readonly inputError = this.locatorForOptional(FormErrorsHarness);

  private readonly advancedParamsButton = this.locatorForOptional(
    MatButtonHarness.with({selector: '.advanced-params-button'}),
  );

  /** Sets the value of the paths input. */
  async setPathsInput(value: string) {
    const input = await this.pathsInput();
    await input.setValue(value);
  }

  /** Gets the value of the paths input. */
  async getPathsInput(): Promise<string> {
    const input = await this.pathsInput();
    return input.getValue();
  }

  /** Checks whether the input has an error. */
  async hasInputError(): Promise<boolean> {
    const error = await this.inputError();
    if (!error) {
      return false;
    }
    return (await error.getErrorMessages()).length > 0;
  }

  /** Checks whether the advanced params are visible. */
  async isAdvancedParamsVisible(): Promise<boolean> {
    const advancedParamsRadioGroup = await this.locatorForOptional(
      MatRadioGroupHarness.with({name: 'collection-level-radio-group'}),
    )();
    return advancedParamsRadioGroup !== null;
  }

  /** Expands the advanced params section. */
  async expandAdvancedParams() {
    if (await this.isAdvancedParamsVisible()) {
      return;
    }
    const button = await this.advancedParamsButton();
    if (!button) {
      throw new Error('Advanced params button is not present');
    }
    await button.click();
  }

  /** Collapses the advanced params section. */
  async collapseAdvancedParams() {
    if (!(await this.isAdvancedParamsVisible())) {
      return;
    }
    const button = await this.advancedParamsButton();
    if (!button) {
      throw new Error('Advanced params button is not present');
    }
    await button.click();
  }

  /** Gets the text of the active collection level. */
  async getActiveCollectionLevelText(): Promise<string | undefined> {
    const advancedParamsRadioGroup = await this.locatorForOptional(
      MatRadioGroupHarness.with({name: 'collection-level-radio-group'}),
    )();

    const checkedRadioButton =
      await advancedParamsRadioGroup?.getCheckedRadioButton();
    return checkedRadioButton?.getLabelText();
  }

  /** Sets the active collection level to the one with the given text. */
  async setActiveCollectionLevel(radioText: string) {
    await this.expandAdvancedParams();
    const advancedParamsRadioGroup = await this.locatorForOptional(
      MatRadioGroupHarness.with({name: 'collection-level-radio-group'}),
    )();
    if (!advancedParamsRadioGroup) {
      throw new Error('Advanced params radio group is not present');
    }
    await advancedParamsRadioGroup.checkRadioButton({label: radioText});
  }
}
