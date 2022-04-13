import {COMMA, ENTER} from '@angular/cdk/keycodes';
import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {UntypedFormControl, Validators} from '@angular/forms';
import {MatChipInputEvent} from '@angular/material/chips';
import {MatDialog} from '@angular/material/dialog';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {OsqueryFlowArgs} from '../../lib/api/api_interfaces';
import {isNonNull} from '../../lib/preconditions';
import {CodeEditor} from '../code_editor/code_editor';

import {OsqueryQueryHelper} from './osquery_query_helper/osquery_query_helper';


/** Form that configures an Osquery flow. */
@Component({
  selector: 'osquery-form',
  templateUrl: './osquery_form.ng.html',
  styleUrls: ['./osquery_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class OsqueryForm extends FlowArgumentForm<OsqueryFlowArgs> {
  private readonly defaultQueryDisplayed = 'SELECT * FROM users LIMIT 10;';

  override makeControls(): Controls<OsqueryFlowArgs> {
    return {
      query: new UntypedFormControl(
          this.defaultQueryDisplayed, Validators.required),
      timeoutMillis: new UntypedFormControl(null, Validators.required),
      ignoreStderrErrors: new UntypedFormControl(null),
      fileCollectionColumns: new UntypedFormControl([]),
    };
  }

  fileCollectionSettingsShown = false;
  lowLevelSettingsShown = false;

  readonly separatorKeysCodes: number[] = [ENTER, COMMA];

  /**
   * Contains the list of columns in the osquery result for file collection.
   * On every mutation of the array, {@link syncFormWithCollectionColumns}
   * should be called to reflect the updated values in the Angular form.
   */
  readonly fileCollectionColumns: string[] = [];

  @ViewChild(CodeEditor) codeEditor?: CodeEditor;

  constructor(private readonly dialog: MatDialog) {
    super();
  }

  override focus(container: HTMLElement): void {
    this.codeEditor?.focus();
  }

  browseTablesClicked(): void {
    const openedDialog = this.dialog.open(OsqueryQueryHelper);

    openedDialog.afterClosed().subscribe(newQueryReceived => {
      if (isNonNull(newQueryReceived)) {
        this.controls.query.setValue(newQueryReceived);
      }
    });  // No need to unsubscribe as it completes when the dialog is closed.
  }

  override convertFlowArgsToFormState(flowArgs: OsqueryFlowArgs):
      OsqueryFlowArgs {
    return {query: '', ...flowArgs};
  }

  override convertFormStateToFlowArgs(formState: OsqueryFlowArgs):
      OsqueryFlowArgs {
    return formState;
  }

  override resetFlowArgs(flowArgs: OsqueryFlowArgs): void {
    if (flowArgs.fileCollectionColumns?.length) {
      this.fileCollectionSettingsShown = true;
    }
    super.resetFlowArgs(flowArgs);
  }

  openCollection() {
    this.fileCollectionSettingsShown = true;
  }

  openSettings() {
    this.lowLevelSettingsShown = true;
  }

  addFileCollectionColumn(event: MatChipInputEvent): void {
    const inputElement = event.chipInput?.inputElement;
    const value = event.value ?? '';

    if (value.trim()) {
      this.fileCollectionColumns.push(value.trim());
      this.syncFormWithCollectionColumns();
    }

    if (inputElement) {
      inputElement.value = '';
    }
  }

  removeFileCollectionColumn(column: string): void {
    const index = this.fileCollectionColumns.indexOf(column);

    if (index >= 0) {
      this.fileCollectionColumns.splice(index, 1);
      this.syncFormWithCollectionColumns();
    }
  }

  private syncFormWithCollectionColumns() {
    this.form.patchValue({
      // Spreading an array with primitive type produces a deep copy, which
      // might be needed for Angular's reactive forms.
      fileCollectionColumns: [...this.fileCollectionColumns],
    });
  }
}
