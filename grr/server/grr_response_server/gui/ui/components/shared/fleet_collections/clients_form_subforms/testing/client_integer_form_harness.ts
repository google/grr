import {ComponentHarness} from '@angular/cdk/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';

/** Harness for the ClientIntegerForm component. */
export class ClientIntegerFormHarness extends ComponentHarness {
  static hostSelector = 'client-integer-form';

  readonly operatorSelect = this.locatorFor(MatSelectHarness);
  readonly valueInput = this.locatorFor(MatInputHarness);

  async getOperator(): Promise<string> {
    return (await this.operatorSelect()).getValueText();
  }
}
