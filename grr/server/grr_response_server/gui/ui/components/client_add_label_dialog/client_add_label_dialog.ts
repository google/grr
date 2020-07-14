import {Component} from '@angular/core';
import {MatDialogRef} from '@angular/material/dialog';

@Component({
  selector: 'client-add-label-dialog',
  templateUrl: './client_add_label_dialog.ng.html',
  styleUrls: ['./client_add_label_dialog.scss'],
})
export class ClientAddLabelDialog {
  label: string = '';

  constructor(public dialogRef: MatDialogRef<ClientAddLabelDialog>) {}

  onCancelClick(): void {
    this.dialogRef.close();
  }

  onAddClick(): void {
    this.dialogRef.close(this.label);
  }
}
