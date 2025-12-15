import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatSelectModule} from '@angular/material/select';

import {
  ListNamedPipesFlowArgs,
  ListNamedPipesFlowArgsPipeEndFilter,
  ListNamedPipesFlowArgsPipeTypeFilter,
} from '../../../lib/api/api_interfaces';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    pipeNameRegex: new FormControl('', {nonNullable: true}),
    procExeRegex: new FormControl('', {nonNullable: true}),
    pipeTypeFilter: new FormControl(
      ListNamedPipesFlowArgsPipeTypeFilter.ANY_TYPE,
      {nonNullable: true},
    ),
    pipeEndFilter: new FormControl(
      ListNamedPipesFlowArgsPipeEndFilter.ANY_END,
      {nonNullable: true},
    ),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** A form that customizes the behaviour of named pipe collection flow. */
@Component({
  selector: 'list-named-pipes-form',
  templateUrl: './list_named_pipes_form.ng.html',
  styleUrls: ['flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListNamedPipesForm extends FlowArgsFormInterface<
  ListNamedPipesFlowArgs,
  Controls
> {
  readonly PipeTypeFilter = ListNamedPipesFlowArgsPipeTypeFilter;
  readonly PipeEndFilter = ListNamedPipesFlowArgsPipeEndFilter;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: ListNamedPipesFlowArgs,
  ): ControlValues<Controls> {
    return {
      pipeNameRegex:
        flowArgs.pipeNameRegex ?? this.controls.pipeNameRegex.defaultValue,
      procExeRegex:
        flowArgs.procExeRegex ?? this.controls.procExeRegex.defaultValue,
      pipeTypeFilter:
        flowArgs.pipeTypeFilter ?? this.controls.pipeTypeFilter.defaultValue,
      pipeEndFilter:
        flowArgs.pipeEndFilter ?? this.controls.pipeEndFilter.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ListNamedPipesFlowArgs {
    return formState;
  }
}
