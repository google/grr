import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatCheckboxModule} from '@angular/material/checkbox';

import {NetstatArgs} from '../../../lib/api/api_interfaces';
import {ControlValues, FlowArgsFormInterface} from './flow_args_form_interface';
import {SubmitButton} from './submit_button';

function makeControls() {
  return {
    listeningOnly: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * Form to configure the netstat flow.
 */
@Component({
  selector: 'netstat-form',
  templateUrl: './netstat_form.ng.html',
  styleUrls: ['./flow_args_form_styles.scss'],
  imports: [CommonModule, MatCheckboxModule, ReactiveFormsModule, SubmitButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NetstatForm extends FlowArgsFormInterface<NetstatArgs, Controls> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(
    flowArgs: NetstatArgs,
  ): ControlValues<Controls> {
    return {
      listeningOnly:
        flowArgs.listeningOnly ?? this.controls.listeningOnly.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(
    formState: ControlValues<Controls>,
  ): NetstatArgs {
    return formState;
  }
}
