import {MatButtonHarness} from '@angular/material/button/testing';
import {MatDialogHarness} from '@angular/material/dialog/testing';
import {MatFormFieldHarness} from '@angular/material/form-field/testing';

/** Harness for the CreateArtifactDialog component. */
export class CreateArtifactDialogHarness extends MatDialogHarness {
  static override hostSelector = 'create-artifact-dialog';

  readonly artifactFormField = this.locatorFor(MatFormFieldHarness);
  readonly createButton = this.locatorFor(
    MatButtonHarness.with({text: 'Create'}),
  );
  readonly cancelButton = this.locatorFor(
    MatButtonHarness.with({text: 'Cancel'}),
  );
}
