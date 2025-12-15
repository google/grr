import {CommonModule} from '@angular/common';
import {Component, inject} from '@angular/core';
import {MatButton} from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';

import {ClientLabel} from '../../lib/models/client';

/** Data passed to the dialog. */
export interface ClientRemoveLabelDialogData {
  label: ClientLabel;
  onRemoveLabel: () => void;
}

/** Dialog to confirm removal of a label. */
@Component({
  selector: 'client-remove-label-dialog',
  templateUrl: './client_remove_label_dialog.ng.html',
  imports: [CommonModule, MatButton, MatDialogModule],
})
export class ClientRemoveLabelDialog {
  dialogRef = inject(MatDialogRef<ClientRemoveLabelDialog>);
  protected readonly dialogData: ClientRemoveLabelDialogData =
    inject(MAT_DIALOG_DATA);

  onRemoveClick(): void {
    this.dialogData.onRemoveLabel();
  }
}
