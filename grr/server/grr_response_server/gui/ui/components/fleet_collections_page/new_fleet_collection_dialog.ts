import {CdkDrag, CdkDragHandle} from '@angular/cdk/drag-drop';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule} from '@angular/material/dialog';
import {MatDividerModule} from '@angular/material/divider';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {RouterModule} from '@angular/router';

import {FormErrors, requiredInput} from '../shared/form/form_validation';

/** Component for creating a new fleet collection. */
@Component({
  selector: 'new-fleet-collection-dialog',
  templateUrl: './new_fleet_collection_dialog.ng.html',
  styleUrls: ['./new_fleet_collection_dialog.scss'],
  imports: [
    CdkDrag,
    CdkDragHandle,
    CommonModule,
    FormErrors,
    MatButtonModule,
    MatDialogModule,
    MatDividerModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NewFleetCollectionDialog {
  protected readonly clientIdControl = new FormControl<string>('', {
    nonNullable: true,
    validators: [requiredInput()],
  });

  protected readonly flowIdControl = new FormControl<string>('', {
    nonNullable: true,
    validators: [requiredInput()],
  });

  protected readonly fleetCollectionIdControl = new FormControl<string>('', {
    nonNullable: true,
    validators: [requiredInput()],
  });
}
