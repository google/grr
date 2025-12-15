import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatRadioModule} from '@angular/material/radio';

import {HashMultipleFilesArgs} from '../../../lib/api/api_interfaces';
import {FlowType} from '../../../lib/models/flow';
import {FormErrors} from '../form/form_validation';
import {GlobExpressionInput} from '../form/glob_expression_form_field/glob_expression_input';
import {
  CollectMultipleFilesForm,
  Controls,
} from './collect_multiple_files_form';
import {ControlValues} from './flow_args_form_interface';
import {ExtFlagsSubform} from './subforms/ext_flags_subform';
import {FileSizeRangeSubform} from './subforms/file_size_range_subform';
import {LiteralMatchSubform} from './subforms/literal_match_subform';
import {RegexMatchSubform} from './subforms/regex_match_subform';
import {TimeRangeSubform} from './subforms/time_range_subform';
import {SubmitButton} from './submit_button';

/** Form that configures a HashMultipleFiles flow. */
@Component({
  selector: 'hash-multiple-files-form',
  templateUrl: './collect_multiple_files_form.ng.html',
  styleUrls: [
    './collect_multiple_files_form.scss',
    './flow_args_form_styles.scss',
  ],
  imports: [
    CommonModule,
    ExtFlagsSubform,
    FileSizeRangeSubform,
    FormErrors,
    GlobExpressionInput,
    LiteralMatchSubform,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatRadioModule,
    ReactiveFormsModule,
    RegexMatchSubform,
    SubmitButton,
    TimeRangeSubform,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HashMultipleFilesForm extends CollectMultipleFilesForm {
  protected override readonly flowType: FlowType = FlowType.HASH_MULTIPLE_FILES;

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): HashMultipleFilesArgs {
    return super.convertFormStateToFlowArgs(formState);
  }

  override resetFlowArgs(flowArgs: HashMultipleFilesArgs): void {
    super.resetFlowArgs(flowArgs);
  }

  override convertFlowArgsToFormState(
    flowArgs: HashMultipleFilesArgs,
  ): ControlValues<Controls> {
    return super.convertFlowArgsToFormState(flowArgs);
  }
}
