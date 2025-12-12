import {CdkDrag, CdkDragHandle} from '@angular/cdk/drag-drop';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  ViewChild,
} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';

import {SafetyLimits} from '../../../lib/models/hunt';
import {RolloutForm} from '../../shared/fleet_collections/rollout_form';

/** Data passed to the dialog. */
export interface ModifyFleetCollectionDialogData {
  currentSafetyLimits: SafetyLimits;
  onSubmit: (clientLimit: bigint, clientRate: number) => void;
}

/** Component that allows configuring Flow arguments. */
@Component({
  selector: 'modify-fleet-collection-dialog',
  templateUrl: './modify_fleet_collection_dialog.ng.html',
  imports: [
    CdkDrag,
    CdkDragHandle,
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    RolloutForm,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModifyFleetCollectionDialog {
  @ViewChild(RolloutForm, {static: false}) rolloutForm!: RolloutForm;

  protected readonly dialogData: ModifyFleetCollectionDialogData =
    inject(MAT_DIALOG_DATA);

  protected submit() {
    const safetyLimits = this.rolloutForm.getFormState();
    this.dialogData.onSubmit(safetyLimits.clientLimit, safetyLimits.clientRate);
  }
}
