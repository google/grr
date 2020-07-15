import {Component, OnInit, Inject} from '@angular/core';
import {MatDialogRef, MAT_DIALOG_DATA} from '@angular/material/dialog';
import {FormControl, ValidatorFn, AbstractControl} from '@angular/forms';
import {Observable} from 'rxjs';
import {startWith, map} from 'rxjs/operators';
import {ClientLabel} from '@app/lib/models/client';

@Component({
  selector: 'client-add-label-dialog',
  templateUrl: './client_add_label_dialog.ng.html',
  styleUrls: ['./client_add_label_dialog.scss'],
})
export class ClientAddLabelDialog {
  newLabelInputControl = new FormControl('', this.labelPresentValidator());
  filteredCurrentLabels: Observable<string[]> = this.newLabelInputControl.valueChanges
    .pipe(
      startWith(''),
      map(value => this.filter(value))
    );

  constructor(private dialogRef: MatDialogRef<ClientAddLabelDialog>,
    @Inject(MAT_DIALOG_DATA) private clientLabels: ReadonlyArray<ClientLabel>) {}

  private filter(value: string): string[] {
    const filterValue = value.toLowerCase();

    return this.clientLabels
      .map(clientLabel => clientLabel.name)
      .filter(label => label.toLowerCase().includes(filterValue));
  }

  labelPresentValidator(): ValidatorFn {
    return (control: AbstractControl): {[key: string]: any} | null => {
      const input = control.value.toLowerCase();
      const matchingLabels = this.clientLabels
        .map(clientLabel => clientLabel.name)
        .filter(label => label.toLowerCase() === input);

      if (matchingLabels.length > 0) {
        return {'alreadyPresentLabel': {value: control.value}};
      }
      return null;
    };
  }

  onCancelClick(): void {
    this.dialogRef.close();
  }

  onAddClick(): void {
    if (this.newLabelInputControl.valid) {
      this.dialogRef.close(this.newLabelInputControl.value);
    }
  }
}
