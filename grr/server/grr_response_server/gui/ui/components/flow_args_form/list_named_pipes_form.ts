import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ListNamedPipesFlowArgs, PipeEndFilter, PipeTypeFilter} from '../../lib/api/api_interfaces';

/** A form that customizes the behaviour of named pipe collection flow. */
@Component({
  selector: 'list-named-pipes-form',
  templateUrl: './list_named_pipes_form.ng.html',
  styleUrls: ['./list_named_pipes_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class ListNamedPipesForm extends
    FlowArgumentForm<ListNamedPipesFlowArgs> {
  readonly PipeTypeFilter = PipeTypeFilter;
  readonly PipeEndFilter = PipeEndFilter;

  override makeControls(): Controls<ListNamedPipesFlowArgs> {
    return {
      pipeNameRegex: new UntypedFormControl(),
      procExeRegex: new UntypedFormControl(),
      pipeTypeFilter: new UntypedFormControl(PipeTypeFilter.ANY_TYPE),
      pipeEndFilter: new UntypedFormControl(PipeEndFilter.ANY_END),
    };
  }

  override convertFlowArgsToFormState(flowArgs: ListNamedPipesFlowArgs):
      ListNamedPipesFlowArgs {
    return flowArgs;
  }

  override convertFormStateToFlowArgs(formState: ListNamedPipesFlowArgs):
      ListNamedPipesFlowArgs {
    return formState;
  }
}
