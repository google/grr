import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {NetstatArgs} from '../../lib/api/api_interfaces';

/**
 * A form that makes it possible to configure the netstat flow.
 */
@Component({
  selector: 'netstat-form',
  templateUrl: './netstat_form.ng.html',
  styleUrls: ['./netstat_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class NetstatForm extends FlowArgumentForm<NetstatArgs> {
  override makeControls(): Controls<NetstatArgs> {
    return {
      listeningOnly: new UntypedFormControl(),
    };
  }
  override convertFlowArgsToFormState(flowArgs: NetstatArgs): NetstatArgs {
    return flowArgs;
  }
  override convertFormStateToFlowArgs(formState: NetstatArgs): NetstatArgs {
    return formState;
  }
}
