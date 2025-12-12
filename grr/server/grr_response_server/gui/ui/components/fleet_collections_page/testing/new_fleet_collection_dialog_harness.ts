import {MatButtonHarness} from '@angular/material/button/testing';
import {MatDialogHarness} from '@angular/material/dialog/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';
import {MatInputHarness} from '@angular/material/input/testing';

/** Harness for the NewFleetCollectionDialog component. */
export class NewFleetCollectionDialogHarness extends MatDialogHarness {
  static override hostSelector = 'new-fleet-collection-dialog';

  private readonly clientIdFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: /Client ID/}),
  );
  private readonly flowIdFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: /Flow ID/}),
  );
  private readonly fleetCollectionIdFormField = this.locatorFor(
    MatFormFieldHarness.with({floatingLabelText: /Fleet Collection ID/}),
  );

  async clientIdInput(): Promise<MatInputHarness> {
    const formField = await this.clientIdFormField();
    const input = await formField.getControl(MatInputHarness);
    if (!input) {
      throw new Error('Client ID input is not found');
    }
    return input;
  }

  async flowIdInput(): Promise<MatInputHarness> {
    const formField = await this.flowIdFormField();
    const input = await formField.getControl(MatInputHarness);
    if (!input) {
      throw new Error('Flow ID input is not found');
    }
    return input;
  }

  async fleetCollectionIdInput(): Promise<MatInputHarness> {
    const formField = await this.fleetCollectionIdFormField();
    const input = await formField.getControl(MatInputHarness);
    if (!input) {
      throw new Error('Fleet Collection ID input is not found');
    }
    return input;
  }

  readonly createFromFlowButton = this.locatorFor(
    MatButtonHarness.with({text: /Next/, selector: '.create-from-flow-button'}),
  );

  readonly createFromFleetCollectionButton = this.locatorFor(
    MatButtonHarness.with({
      text: /Next/,
      selector: '.create-from-fleet-collection-button',
    }),
  );

  readonly cancelButton = this.locatorFor(
    MatButtonHarness.with({text: /Cancel/}),
  );
}
