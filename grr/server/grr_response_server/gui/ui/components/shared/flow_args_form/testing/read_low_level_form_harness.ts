import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the ReadLowLevelForm component. */
export class ReadLowLevelFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'read-low-level-form';

  private readonly pathFormFieldHarness = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Absolute path'}),
  );
  private readonly lengthFormFieldHarness = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Length'}),
  );
  private readonly offsetFormFieldHarness = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Offset'}),
  );

  /** Sets the path input value. */
  async setPathInput(path: string): Promise<void> {
    const pathFormFieldHarness = await this.pathFormFieldHarness();
    const pathInputHarness =
      await pathFormFieldHarness.getControl(MatInputHarness);
    await pathInputHarness!.setValue(path);
  }

  /** Returns the path input value. */
  async getPathInput(): Promise<string> {
    const pathFormFieldHarness = await this.pathFormFieldHarness();
    const pathInputHarness =
      await pathFormFieldHarness.getControl(MatInputHarness);
    return pathInputHarness!.getValue();
  }

  /** Returns the path input errors. */
  async getPathErrors(): Promise<string[]> {
    const pathFormFieldHarness = await this.pathFormFieldHarness();
    return pathFormFieldHarness.getTextErrors();
  }

  /** Sets the length input value. */
  async setLengthInput(length: string): Promise<void> {
    const lengthFormFieldHarness = await this.lengthFormFieldHarness();
    const lengthInputHarness =
      await lengthFormFieldHarness.getControl(MatInputHarness);
    await lengthInputHarness!.setValue(length);
  }

  /** Returns the length input value. */
  async getLengthInput(): Promise<string> {
    const lengthFormFieldHarness = await this.lengthFormFieldHarness();
    const lengthInputHarness =
      await lengthFormFieldHarness.getControl(MatInputHarness);
    return lengthInputHarness!.getValue();
  }

  /** Returns the length input errors. */
  async getLengthErrors(): Promise<string[]> {
    const lengthFormFieldHarness = await this.lengthFormFieldHarness();
    return lengthFormFieldHarness.getTextErrors();
  }

  /** Sets the offset input value. */
  async setOffsetInput(offset: string): Promise<void> {
    const offsetFormFieldHarness = await this.offsetFormFieldHarness();
    const offsetInputHarness =
      await offsetFormFieldHarness.getControl(MatInputHarness);
    await offsetInputHarness!.setValue(offset);
  }

  /** Returns the offset input value. */
  async getOffsetInput(): Promise<string> {
    const offsetFormFieldHarness = await this.offsetFormFieldHarness();
    const offsetInputHarness =
      await offsetFormFieldHarness.getControl(MatInputHarness);
    return offsetInputHarness!.getValue();
  }
}
