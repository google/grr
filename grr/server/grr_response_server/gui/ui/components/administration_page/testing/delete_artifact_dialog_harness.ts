import {MatButtonHarness} from '@angular/material/button/testing';
import {MatDialogHarness} from '@angular/material/dialog/testing';

/** Harness for the DeleteArtifactDialog component. */
export class DeleteArtifactDialogHarness extends MatDialogHarness {
  static override hostSelector = 'delete-artifact-dialog';

  readonly cancelButton = this.locatorFor(
    MatButtonHarness.with({text: 'Cancel'}),
  );
  readonly deleteButton = this.locatorFor(
    MatButtonHarness.with({text: 'Delete'}),
  );

  async clickDeleteButton(): Promise<void> {
    return (await this.deleteButton()).click();
  }

  async clickCancelButton(): Promise<void> {
    return (await this.cancelButton()).click();
  }
}
