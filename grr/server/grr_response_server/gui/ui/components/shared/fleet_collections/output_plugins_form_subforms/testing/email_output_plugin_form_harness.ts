import {ComponentHarness} from '@angular/cdk/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for interacting with EmailOutputPluginForm in tests. */
export class EmailOutputPluginFormHarness extends ComponentHarness {
  static hostSelector = 'email-output-plugin-form';

  readonly formField = this.locatorFor(MatFormFieldHarness);
  readonly emailInput = this.locatorFor(MatInputHarness);

  async getControl(): Promise<MatInputHarness> {
    const formField = await this.formField();
    return (await formField.getControl(MatInputHarness))!;
  }
}
