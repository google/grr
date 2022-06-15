import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {NetstatArgs} from '../../lib/api/api_interfaces';

function makeControls() {
  return {
    listeningOnly: new FormControl(false, {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/**
 * A form that makes it possible to configure the netstat flow.
 */
@Component({
  selector: 'netstat-form',
  templateUrl: './netstat_form.ng.html',
  styleUrls: ['./netstat_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class NetstatForm extends FlowArgumentForm<NetstatArgs, Controls> {
  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: NetstatArgs) {
    return {
      listeningOnly:
          flowArgs.listeningOnly ?? this.controls.listeningOnly.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return formState;
  }
}
