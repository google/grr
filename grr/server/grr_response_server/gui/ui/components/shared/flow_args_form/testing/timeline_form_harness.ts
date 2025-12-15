import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

import {BaseFlowFormHarness} from './base_flow_form_harness';

/** Harness for the TimelineForm component. */
export class TimelineFormHarness extends BaseFlowFormHarness {
  static override hostSelector = 'timeline-form';

  private readonly rootDirectoryFormFieldHarness = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: 'Root directory'}),
  );

  /** Sets the root directory input value. */
  async setRootDirectoryInput(path: string): Promise<void> {
    const rootDirectoryFormFieldHarness =
      await this.rootDirectoryFormFieldHarness();
    const rootDirectoryInputHarness =
      await rootDirectoryFormFieldHarness.getControl(MatInputHarness);
    await rootDirectoryInputHarness!.setValue(path);
  }

  /** Returns the root directory input value. */
  async getRootDirectoryInput(): Promise<string> {
    const rootDirectoryFormFieldHarness =
      await this.rootDirectoryFormFieldHarness();
    const rootDirectoryInputHarness =
      await rootDirectoryFormFieldHarness.getControl(MatInputHarness);
    return rootDirectoryInputHarness!.getValue();
  }

  /** Returns the root directory input errors. */
  async getRootDirectoryErrors(): Promise<string[]> {
    const rootDirectoryFormFieldHarness =
      await this.rootDirectoryFormFieldHarness();
    return rootDirectoryFormFieldHarness.getTextErrors();
  }

  async getRootDirectoryWarnings(): Promise<string[]> {
    const rootDirectoryFormFieldHarness =
      await this.rootDirectoryFormFieldHarness();
    return rootDirectoryFormFieldHarness.getTextHints();
  }
}
