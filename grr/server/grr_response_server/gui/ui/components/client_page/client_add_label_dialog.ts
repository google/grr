import {CommonModule} from '@angular/common';
import {Component, computed, inject} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {
  ReactiveFormsModule,
  UntypedFormControl,
  ValidatorFn,
} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatButton} from '@angular/material/button';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import {MatInputModule} from '@angular/material/input';

import {ClientLabel} from '../../lib/models/client';

/** Data passed to the dialog. */
export interface ClientAddLabelDialogData {
  clientLabels: readonly ClientLabel[];
  allLabels: readonly string[];
  onAddLabel: (label: string) => void;
}

/** Dialog that displays a form to add a label to a client. */
@Component({
  selector: 'client-add-label-dialog',
  templateUrl: './client_add_label_dialog.ng.html',
  imports: [
    CommonModule,
    MatAutocompleteModule,
    MatButton,
    MatDialogModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
})
export class ClientAddLabelDialog {
  protected readonly dialogRef = inject(MatDialogRef<ClientAddLabelDialog>);
  protected readonly dialogData: ClientAddLabelDialogData =
    inject(MAT_DIALOG_DATA);

  readonly labelInputControl = new UntypedFormControl(
    '',
    this.labelValidator(),
  );

  protected readonly labelInput = toSignal(this.labelInputControl.valueChanges);
  readonly isNewLabel = computed(
    () =>
      this.labelInput() !== undefined &&
      this.labelInput().trim() !== '' &&
      !this.dialogData.allLabels.includes(this.labelInput().trim()),
  );
  readonly suggestedLabels = computed(() =>
    this.dialogData.allLabels
      .filter((label) => {
        // Label already present in client.
        if (
          this.dialogData.clientLabels.some(
            (setLabel) => setLabel.name === label,
          )
        ) {
          return false;
        }
        return label.includes(this.labelInput()?.trim() ?? '');
      })
      .sort(),
  );

  private labelValidator(): ValidatorFn {
    return (control) => {
      if (control.value === undefined) {
        return null;
      }
      const inputLabel = control.value.trim();
      if (
        this.dialogData.clientLabels
          .map((label) => label.name)
          .includes(inputLabel)
      ) {
        return {'alreadyPresentLabel': {value: inputLabel}};
      }
      return null;
    };
  }

  protected onAddClick(): void {
    if (this.labelInputControl.valid) {
      this.dialogData.onAddLabel(this.labelInputControl.value.trim());
      this.dialogRef.close(true);
    }
  }
}
