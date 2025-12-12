import {ComponentHarness} from '@angular/cdk/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatErrorHarness} from '@angular/material/form-field/testing';

/** Harness for the ClientOsForm component. */
export class ClientOsFormHarness extends ComponentHarness {
  static hostSelector = 'client-os-form';

  readonly errorMessage = this.locatorForOptional(MatErrorHarness);

  readonly windowsCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Windows'}),
  );
  readonly darwinCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Darwin'}),
  );
  readonly linuxCheckbox = this.locatorFor(
    MatCheckboxHarness.with({label: 'Linux'}),
  );

  async getErrorText(): Promise<string | undefined> {
    const errorMessage = await this.errorMessage();
    return errorMessage?.getText();
  }
}
