import {COMMA, ENTER, SPACE} from '@angular/cdk/keycodes';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatAutocompleteModule} from '@angular/material/autocomplete';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ListProcessesArgs} from '../../../lib/api/api_interfaces';
import {CommaSeparatedNumberValueAccessor} from '../form/comma_separated_input/comma_separated_value_accessor';
import {FormErrors, integerArrayValidator} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    pids: new FormControl<readonly number[]>([], {
      nonNullable: true,
      validators: [integerArrayValidator()],
    }),
    filenameRegex: new FormControl('', {nonNullable: true}),
    fetchBinaries: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** A form that configures the ListProcesses flow. */
@Component({
  selector: 'list-processes-form',
  templateUrl: './list_processes_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommaSeparatedNumberValueAccessor,
    CommonModule,
    FormErrors,
    FormsModule,
    MatAutocompleteModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListProcessesForm extends FlowArgsFormInterface<
  ListProcessesArgs,
  Controls
> {
  protected readonly SEPARATOR_KEY_CODES = [ENTER, COMMA, SPACE];

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: ListProcessesArgs,
  ): ControlValues<Controls> {
    return {
      fetchBinaries:
        flowArgs.fetchBinaries ?? this.controls.fetchBinaries.defaultValue,
      filenameRegex:
        flowArgs.filenameRegex ?? this.controls.filenameRegex.defaultValue,
      pids: flowArgs.pids ?? this.controls.pids.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ListProcessesArgs {
    return formState;
  }
}
