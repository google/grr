import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';

import {ControlValues, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {OnlineNotificationArgs} from '../../lib/api/api_interfaces';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';

function makeControls() {
  return {
    email: new FormControl('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;


/**
 * A form that makes it possible to configure the OnlineNotification flow.
 */
@Component({
  selector: 'online-notification-form',
  templateUrl: './online_notification_form.ng.html',
  styleUrls: ['./online_notification_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,

})
export class OnlineNotificationForm extends
    FlowArgumentForm<OnlineNotificationArgs, Controls> {
  constructor(private readonly clientPageGlobalStore: ClientPageGlobalStore) {
    super();
  }

  readonly client$ = this.clientPageGlobalStore.selectedClient$;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: OnlineNotificationArgs) {
    return {
      email: flowArgs.email ?? this.controls.email.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return formState;
  }
}
