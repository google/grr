import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatCheckboxModule} from '@angular/material/checkbox';
import {MatTooltipModule} from '@angular/material/tooltip';

import {ListContainersFlowArgs} from '../../../lib/api/api_interfaces';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    inspectHostroot: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a ListContainers flow. */
@Component({
  selector: 'list-containers-form',
  templateUrl: './list_containers_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatCheckboxModule,
    MatTooltipModule,
    ReactiveFormsModule,
    SubmitButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListContainersForm extends FlowArgsFormInterface<
  ListContainersFlowArgs,
  Controls
> {
  override makeControls(): Controls {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: ListContainersFlowArgs,
  ): ControlValues<Controls> {
    return {
      inspectHostroot:
        flowArgs.inspectHostroot ?? this.controls.inspectHostroot.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): ListContainersFlowArgs {
    return formState;
  }
}
