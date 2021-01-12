import {Component, Inject} from '@angular/core';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';

import {FlowDescriptor} from '../../lib/models/flow';

/** Flow descriptor and args to display in the dialog. */
export interface FlowArgsDialogData {
  readonly flowDescriptor: FlowDescriptor;
  readonly flowArgs: unknown;
}

/** Dialog that displays flow arguments. */
@Component({
  selector: 'client-add-label-dialog',
  templateUrl: './flow_args_dialog.ng.html',
  styleUrls: ['./flow_args_dialog.scss'],
})
export class FlowArgsDialog {
  readonly flowDescriptor: FlowDescriptor;

  constructor(
      @Inject(MAT_DIALOG_DATA) data: FlowArgsDialogData,
      readonly dialogRef: MatDialogRef<FlowArgsDialog>) {
    this.flowDescriptor = {
      ...data.flowDescriptor,
      defaultArgs: data.flowArgs,
    };
  }
}
