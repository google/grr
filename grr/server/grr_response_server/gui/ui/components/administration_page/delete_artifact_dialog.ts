import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {MatButton} from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';

import {ArtifactDescriptor} from '../../lib/models/flow';

/** Data passed to the dialog. */
export interface DeleteArtifactDialogData {
  artifact: ArtifactDescriptor;
  onDeleteArtifact: () => void;
}

/** Dialog to confirm deletion of an artifact. */
@Component({
  changeDetection: ChangeDetectionStrategy.Eager,
  selector: 'delete-artifact-dialog',
  templateUrl: './delete_artifact_dialog.ng.html',
  imports: [CommonModule, MatButton, MatDialogModule],
})
export class DeleteArtifactDialog {
  dialogRef = inject(MatDialogRef<DeleteArtifactDialog>);
  protected readonly dialogData: DeleteArtifactDialogData =
    inject(MAT_DIALOG_DATA);

  onDeleteClick(): void {
    this.dialogData.onDeleteArtifact();
  }
}
