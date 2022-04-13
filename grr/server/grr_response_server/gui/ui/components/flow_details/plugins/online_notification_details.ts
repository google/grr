import {Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {OnlineNotificationArgs} from '../../../lib/api/api_interfaces';
import {Flow, FlowState} from '../../../lib/models/flow';

import {Plugin} from './plugin';


/**
 * Details about an OnlineNotification flow.
 */
@Component({
  selector: 'online-notification-details',
  templateUrl: './online_notification_details.ng.html',
})
export class OnlineNotificationDetails extends Plugin {
  /** Observable of the arguments that the flow was created with. */
  readonly args$: Observable<OnlineNotificationArgs> =
      this.flow$.pipe(map(flow => flow.args as OnlineNotificationArgs));

  readonly title$ = this.args$.pipe(map(args => `Recipient: ${args.email}`));

  override getResultDescription(flow: Flow): string|undefined {
    if (flow.state === FlowState.FINISHED) {
      return '1 email sent';
    } else {
      return super.getResultDescription(flow);
    }
  }
}
