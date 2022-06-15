import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListNamedPipesFlowArgs, PipeEndFilter, PipeTypeFilter} from '../../lib/api/api_interfaces';

function makeControls() {
  return {
    pipeNameRegex: new FormControl('', {nonNullable: true}),
    procExeRegex: new FormControl('', {nonNullable: true}),
    pipeTypeFilter:
        new FormControl(PipeTypeFilter.ANY_TYPE, {nonNullable: true}),
    pipeEndFilter: new FormControl(PipeEndFilter.ANY_END, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** A form that customizes the behaviour of named pipe collection flow. */
@Component({
  selector: 'list-named-pipes-form',
  templateUrl: './list_named_pipes_form.ng.html',
  styleUrls: ['./list_named_pipes_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListNamedPipesForm extends
    FlowArgumentForm<ListNamedPipesFlowArgs, Controls> {
  readonly PipeTypeFilter = PipeTypeFilter;
  readonly PipeEndFilter = PipeEndFilter;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: ListNamedPipesFlowArgs) {
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

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return formState;
  }
}
