import {COMMA, ENTER} from '@angular/cdk/keycodes';
import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {FormControl, Validators} from '@angular/forms';
import {MatChipInputEvent} from '@angular/material/chips';
import {MatDialog} from '@angular/material/dialog';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {OsqueryFlowArgs} from '../../lib/api/api_interfaces';
import {isNonNull} from '../../lib/preconditions';
import {CodeEditor, HighlightMode} from '../code_editor/code_editor';

import {OsqueryQueryHelper} from './osquery_query_helper/osquery_query_helper';

const DEFAULT_QUERY = 'SELECT * FROM users LIMIT 10;';

function makeControls() {
  return {
    query: new FormControl(
        DEFAULT_QUERY, {nonNullable: true, validators: [Validators.required]}),
    timeoutMillis: new FormControl(
        0, {nonNullable: true, validators: [Validators.required]}),
    ignoreStderrErrors: new FormControl(false, {nonNullable: true}),
    fileCollectionColumns:
        new FormControl<ReadonlyArray<string>>([], {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures an Osquery flow. */
@Component({
  selector: 'osquery-form',
  templateUrl: './osquery_form.ng.html',
  styleUrls: ['./osquery_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryForm extends FlowArgumentForm<OsqueryFlowArgs, Controls> {
  readonly HighlightMode = HighlightMode;

  override makeControls() {
    return makeControls();
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

  override convertFlowArgsToFormState(flowArgs: OsqueryFlowArgs) {
    return {
      fileCollectionColumns: flowArgs.fileCollectionColumns ??
          this.controls.fileCollectionColumns.defaultValue,
      ignoreStderrErrors: flowArgs.ignoreStderrErrors ??
          this.controls.ignoreStderrErrors.defaultValue,
      timeoutMillis: Number(
          flowArgs.timeoutMillis ?? this.controls.timeoutMillis.defaultValue),
      query: flowArgs.query ?? this.controls.query.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      ...formState,
      timeoutMillis: formState.timeoutMillis?.toString(),
    };
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
