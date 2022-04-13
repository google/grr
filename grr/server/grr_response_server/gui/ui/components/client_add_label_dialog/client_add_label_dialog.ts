import {Component, Inject} from '@angular/core';
import {UntypedFormControl, ValidatorFn} from '@angular/forms';
import {MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {Observable} from 'rxjs';
import {filter, map, withLatestFrom} from 'rxjs/operators';

import {ClientLabel} from '../../lib/models/client';
import {isNonNull} from '../../lib/preconditions';
import {ConfigGlobalStore} from '../../store/config_global_store';

/** Dialog that displays a form to add a label to a client. */
@Component({
  selector: 'client-add-label-dialog',
  templateUrl: './client_add_label_dialog.ng.html',
  styleUrls: ['./client_add_label_dialog.scss'],
})
export class ClientAddLabelDialog {
  constructor(
      private readonly dialogRef: MatDialogRef<ClientAddLabelDialog>,
      @Inject(MAT_DIALOG_DATA) private readonly clientLabels:
          ReadonlyArray<ClientLabel>,
      private readonly configGlobalStore: ConfigGlobalStore) {}

  readonly labelInputControl =
      new UntypedFormControl('', this.labelValidator());
  private readonly allClientsLabels$ = this.configGlobalStore.clientsLabels$;

  /**
   * An internal observable, which emits the following combined:
   *    * a string containing the trimmed input
   *    * a string[] containing all labels used in GRR
   */
  private readonly inputAndAllLabels$ =
      this.labelInputControl.valueChanges.pipe(
          filter(isNonNull),
          map(input => input.trim()),
          withLatestFrom(this.allClientsLabels$),
      );

  /**
   * An observable emitting true when the input label is not exactly matching
   *  any of the existing labels in GRR, and false otherwise.
   */
  readonly isNewLabel$: Observable<boolean> = this.inputAndAllLabels$.pipe(
      map(([input, allLabels]) => {
        if (input === '') return false;
        return !allLabels.includes(input);
      }),
  );

  /**
   * An observable emitting an array of possible labels, for autocompletion.
   *  The array doesn't contain labels already assigned to the client.
   */
  readonly suggestedLabels$: Observable<string[]> =
      this.inputAndAllLabels$.pipe(
          map(([input, allLabels]) => {
            if (input === '') return [];
            return allLabels.filter(label => label.includes(input));
          }),
          map(filteredLabels =>
                  filteredLabels.filter(label => !this.clientHasLabel(label))),
      );

  private clientHasLabel(label: string): boolean {
    const trimmedLabel = label.trim();
    return this.clientLabels.map(clientLabel => clientLabel.name)
        .includes(trimmedLabel);
  }

  private labelValidator(): ValidatorFn {
    return (control) => {
      if (control.value === undefined) {
        return null;
      }
      const inputLabel = control.value.trim();

      if (this.clientHasLabel(inputLabel)) {
        return {'alreadyPresentLabel': {value: inputLabel}};
      }

      return null;
    };
  }

  onCancelClick(): void {
    this.dialogRef.close(undefined);
  }

  onAddClick(event?: Event): void {
    event?.preventDefault();

    if (this.labelInputControl.valid) {
      this.dialogRef.close(this.labelInputControl.value.trim());
    }
  }
}
