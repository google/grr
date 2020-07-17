import {Component, OnInit, Inject} from '@angular/core';
import {MatDialogRef, MAT_DIALOG_DATA} from '@angular/material/dialog';
import {FormControl, ValidatorFn, AbstractControl} from '@angular/forms';
import {Observable} from 'rxjs';
import {startWith, map, combineLatest} from 'rxjs/operators';
import {ClientLabel} from '@app/lib/models/client';
import {ConfigFacade} from '@app/store/config_facade';

@Component({
  selector: 'client-add-label-dialog',
  templateUrl: './client_add_label_dialog.ng.html',
  styleUrls: ['./client_add_label_dialog.scss'],
})
export class ClientAddLabelDialog {
  readonly newLabelInputControl = new FormControl('', this.labelPresentValidator());
  private readonly existingLabels$ = this.configFacade.clientsLabels$;
  readonly filteredLabels: Observable<string[]> = this.newLabelInputControl.valueChanges
    .pipe(
      startWith(''),
      combineLatest(this.existingLabels$),
      map(([input, existingLabels]) => this.filter(input, existingLabels))
    );

  constructor(
    readonly dialogRef: MatDialogRef<ClientAddLabelDialog>,
    @Inject(MAT_DIALOG_DATA) private clientLabels: ReadonlyArray<ClientLabel>,
    private readonly configFacade: ConfigFacade
  ) {}

  private filter(value: string, existingLabels: ClientLabel[]): string[] {
    const filterValue = value.toLowerCase();

    return existingLabels
      .map(clientLabel => clientLabel.name)
      .filter(label => label.toLowerCase().includes(filterValue));
  }

  labelPresentValidator(): ValidatorFn {
    return (control: AbstractControl): {[key: string]: any} | null => {
      if (control.value === undefined) {
        return null;
      }

      if (this.clientHasLabel(control.value)) {
        return {'alreadyPresentLabel': {value: control.value}};
      }

      return null;
    };
  }

  clientHasLabel(label: string): boolean {
    const matchingLabels = this.clientLabels
      .map(clientLabel => clientLabel.name)
      .find(labelItem => labelItem.toLowerCase() === label.toLowerCase());

    if (matchingLabels !== undefined) {
      return true;
    }

    return false;
  }

  onCancelClick(): void {
    this.dialogRef.close(undefined);
  }

  onAddClick(): void {
    if (this.newLabelInputControl.valid) {
      this.dialogRef.close(this.newLabelInputControl.value);
    }
  }
}
