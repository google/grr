import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';

import {ReadLowLevelArgs} from '../../../lib/api/api_interfaces';
import {ByteValueAccessor} from '../form/byte_input/byte_value_accessor';
import {FormErrors, minValue, requiredInput} from '../form/form_validation';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    path: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
    // ByteValueAccessor inputs can be null when input is invalid.
    length: new FormControl<number>(42, {
      validators: [requiredInput(), minValue(1)],
    }),
    offset: new FormControl<number>(0),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the read_low_level flow.
 */
@Component({
  selector: 'read-low-level-form',
  templateUrl: './read_low_level_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    ByteValueAccessor,
    CommonModule,
    FormErrors,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReadLowLevelForm extends FlowArgsFormInterface<
  ReadLowLevelArgs,
  Controls
> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: ReadLowLevelArgs,
  ): ControlValues<Controls> {
    return {
      path: flowArgs.path ?? this.controls.path.defaultValue,
      length: Number(flowArgs.length ?? this.controls.length.defaultValue),
      offset: Number(flowArgs.offset ?? this.controls.offset.defaultValue),
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ReadLowLevelArgs {
    return {
      length: formState.length?.toString(),
      offset: formState.offset?.toString(),
      path: formState.path?.trim(),
    };
  }
}
