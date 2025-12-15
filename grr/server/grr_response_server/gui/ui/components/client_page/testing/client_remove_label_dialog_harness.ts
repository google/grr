import {MatButtonHarness} from '@angular/material/button/testing';
import {MatDialogHarness} from '@angular/material/dialog/testing';

/** Harness for the ClientRemoveLabelDialog component. */
export class ClientRemoveLabelDialogHarness extends MatDialogHarness {
  static override hostSelector = 'client-remove-label-dialog';

  readonly cancelButton = this.locatorFor(
    MatButtonHarness.with({text: 'Cancel'}),
  );
  readonly removeButton = this.locatorFor(
    MatButtonHarness.with({text: 'Remove'}),
  );

  async clickRemoveButton(): Promise<void> {
    return (await this.removeButton()).click();
  }

  async clickCancelButton(): Promise<void> {
    return (await this.cancelButton()).click();
  }
}
