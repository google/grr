import {CdkDrag, CdkDragHandle} from '@angular/cdk/drag-drop';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatDialogModule, MatDialogRef} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {GlobalStore} from '../../store/global_store';

/** Dialog that displays a form to upload a new artifact. */
@Component({
  changeDetection: ChangeDetectionStrategy.Eager,
  selector: 'create-artifact-dialog',
  templateUrl: './create_artifact_dialog.ng.html',
  styleUrls: ['./create_artifact_dialog.scss'],
  imports: [
    CdkDrag,
    CdkDragHandle,
    CommonModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
  ],
})
export class CreateArtifactDialog {
  private readonly globalStore = inject(GlobalStore);
  private readonly dialogRef = inject(MatDialogRef<CreateArtifactDialog>);

  readonly artifactFormControl = new FormControl<string>('');

  protected onCreateClick(): void {
    this.globalStore.uploadArtifact(this.artifactFormControl.value ?? '');
    this.dialogRef.close(true);
  }
}
