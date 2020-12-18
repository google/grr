import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {shareReplay} from 'rxjs/operators';
import {MatDialog} from '@angular/material/dialog';
import {MatChipInputEvent} from '@angular/material/chips';
import {COMMA, ENTER} from '@angular/cdk/keycodes';

import {OsqueryArgs} from '../../lib/api/api_interfaces';
import {OsqueryQueryHelper} from './osquery_query_helper/osquery_query_helper';
import {isNonNull} from '@app/lib/preconditions';


/** Form that configures an Osquery flow. */
@Component({
  selector: 'osquery-form',
  templateUrl: './osquery_form.ng.html',
  styleUrls: ['./osquery_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryForm extends FlowArgumentForm<OsqueryArgs> implements
    OnInit {
  private readonly defaultQueryDisplayed = 'SELECT * FROM users LIMIT 10;';

  readonly form = new FormGroup({
    query: new FormControl(this.defaultQueryDisplayed, Validators.required),
    timeoutMillis: new FormControl(null, Validators.required),
    ignoreStderrErrors: new FormControl(null),
    fileCollectColumns: new FormControl([]),
  });

  fileCollectionSettingsShown = false;
  lowLevelSettingsShown = false;

  readonly separatorKeysCodes: number[] = [ENTER, COMMA];

  get fileCollectColumnsControl() {
    const control = this.form.get('fileCollectColumns');
    if (!control) {
      throw Error('fileCollectColumns form control is null');
    }

    return control;
  }
  get fileCollectColumns() {
    return this.fileCollectColumnsControl?.value as Array<string>;
  }

  @Output() readonly formValues$ = this.form.valueChanges.pipe(shareReplay(1));
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  constructor(private readonly dialog: MatDialog) {
    super();
  }

  browseTablesClicked(): void {
    const openedDialog = this.dialog.open(OsqueryQueryHelper);

    openedDialog.afterClosed().subscribe(newQueryReceived => {
      if (isNonNull(newQueryReceived)) {
        this.overwriteQuery(newQueryReceived);
      }
    }); // No need to unsubscribe as it completes when the dialog is closed.
  }

  ngOnInit(): void {
    if (this.defaultFlowArgs.fileCollectColumns &&
        this.defaultFlowArgs.fileCollectColumns.length > 0) {
        this.fileCollectionSettingsShown = true;
    }

    this.form.patchValue(this.defaultFlowArgs);
  }

  openCollection() {
    this.fileCollectionSettingsShown = true;
  }

  openSettings() {
    this.lowLevelSettingsShown = true;
  }

  addFileCollectedColumn(event: MatChipInputEvent): void {
    const inputElement = event.input;
    const value = event.value ?? '';

    if (value.trim()) {
      this.fileCollectColumns.push(value.trim());
      this.fileCollectColumnsControl.markAsDirty();
    }

    if (inputElement) {
      inputElement.value = '';
    }
  }

  removeFileCollectedColumn(column: string): void {
    const index = this.fileCollectColumns.indexOf(column);

    if (index >= 0) {
      this.fileCollectColumns.splice(index, 1);
      this.fileCollectColumnsControl.markAsDirty();
    }
  }

  private overwriteQuery(newValue: string): void {
    this.form.patchValue({
      query: newValue,
    });
  }
}
