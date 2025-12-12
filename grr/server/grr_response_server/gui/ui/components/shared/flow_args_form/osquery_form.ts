import {COMMA, ENTER} from '@angular/cdk/keycodes';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipInputEvent, MatChipsModule} from '@angular/material/chips';
import {MatDialog} from '@angular/material/dialog';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';
import {windowOpen} from 'safevalues/dom';
import {OsqueryFlowArgs} from '../../../lib/api/api_interfaces';
import {
  FormControlWithWarnings,
  FormErrors,
  FormWarnings,
  literalKnowledgebaseExpressionWarning,
  requiredInput,
} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {OsqueryQueryHelper} from './osquery_query_helper/osquery_query_helper';
import {SubmitButton} from './submit_button';

const DEFAULT_QUERY = 'SELECT * FROM users LIMIT 10;';

function makeControls() {
  return {
    query: new FormControl(DEFAULT_QUERY, {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    timeoutMillis: new FormControl(0, {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    ignoreStderrErrors: new FormControl(false, {nonNullable: true}),
    fileCollectionColumns: new FormControl<readonly string[]>([], {
      nonNullable: true,
    }),
    configurationPath: new FormControlWithWarnings('', {
      nonNullable: true,
      validators: [literalKnowledgebaseExpressionWarning()],
    }),
    configurationContent: new FormControl('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures an Osquery flow. */
@Component({
  selector: 'osquery-form',
  templateUrl: './osquery_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    FormErrors,
    FormWarnings,
    FormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryForm extends FlowArgsFormInterface<
  OsqueryFlowArgs,
  Controls
> {
  private readonly dialog = inject(MatDialog);

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

  browseTablesClicked(): void {
    const openedDialog = this.dialog.open(OsqueryQueryHelper);

    openedDialog.afterClosed().subscribe((newQueryReceived) => {
      if (newQueryReceived != null) {
        this.controls.query.setValue(newQueryReceived);
      }
    }); // No need to unsubscribe as it completes when the dialog is closed.
  }

  override convertFlowArgsToFormState(
    flowArgs: OsqueryFlowArgs,
  ): ControlValues<Controls> {
    return {
      fileCollectionColumns:
        flowArgs.fileCollectionColumns ??
        this.controls.fileCollectionColumns.defaultValue,
      ignoreStderrErrors:
        flowArgs.ignoreStderrErrors ??
        this.controls.ignoreStderrErrors.defaultValue,
      timeoutMillis: Number(
        flowArgs.timeoutMillis ?? this.controls.timeoutMillis.defaultValue,
      ),
      query: flowArgs.query ?? this.controls.query.defaultValue,
      configurationPath:
        flowArgs.configurationPath ??
        this.controls.configurationPath.defaultValue,
      configurationContent:
        flowArgs.configurationContent ??
        this.controls.configurationContent.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): OsqueryFlowArgs {
    return {
      ...formState,
      timeoutMillis: formState.timeoutMillis?.toString(),
    };
  }

  override resetFlowArgs(flowArgs: OsqueryFlowArgs): void {
    // Show the settings by default when resetting the flow args to make sure
    // the user can see all settings they previously configured.
    this.fileCollectionSettingsShown = true;
    this.lowLevelSettingsShown = true;

    super.resetFlowArgs(flowArgs);
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

  protected openLinkInNewTab(url: string) {
    windowOpen(window, url, '_blank');
  }
}
