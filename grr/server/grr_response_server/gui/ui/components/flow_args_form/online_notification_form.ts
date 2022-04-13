import {ChangeDetectionStrategy, Component} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';

import {Controls, FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {OnlineNotificationArgs} from '../../lib/api/api_interfaces';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';

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
    FlowArgumentForm<OnlineNotificationArgs> {
  constructor(private readonly clientPageGlobalStore: ClientPageGlobalStore) {
    super();
  }

  readonly client$ = this.clientPageGlobalStore.selectedClient$;

  override makeControls(): Controls<OnlineNotificationArgs> {
    return {
      email: new UntypedFormControl(''),
    };
  }

  override convertFlowArgsToFormState(flowArgs: OnlineNotificationArgs):
      OnlineNotificationArgs {
    return {
      email: '',
      ...flowArgs,
    };
  }

  override convertFormStateToFlowArgs(formState: OnlineNotificationArgs):
      OnlineNotificationArgs {
    return formState;
  }
}
