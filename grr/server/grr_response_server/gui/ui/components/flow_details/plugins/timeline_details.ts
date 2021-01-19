import {Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {TimelineArgs} from '../../../lib/api/api_interfaces';
import {HttpApiService} from '../../../lib/api/http_api_service';
import {FlowState} from '../../../lib/models/flow';

import {Plugin} from './plugin';

/**
 * A component with the details about the timeline flow.
 *
 * The timeline flow recursively collects metadata about all files in the file-
 * system (or a specified directory).
 */
@Component({
  selector: 'timeline-details',
  templateUrl: './timeline_details.ng.html',
  styleUrls: ['./timeline_details.scss'],
})
export class TimelineDetails extends Plugin {
  readonly FlowState: typeof FlowState = FlowState;

  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }

  /** Observable of the state that the flow currently is in. */
  readonly state$: Observable<FlowState> =
      this.flowListEntry$.pipe(map(flowListEntry => flowListEntry.flow.state));

  /** Observable of the arguments that the flow was created with. */
  readonly args$: Observable<TimelineArgs> = this.flowListEntry$.pipe(
      map(flowListEntry => flowListEntry.flow.args as TimelineArgs));

  /**
   * Observable with URL to download the collected timeline in the body format.
   */
  readonly bodyFileUrl$: Observable<string> =
      this.flowListEntry$.pipe(map(flowListEntry => {
        const clientId = flowListEntry.flow.clientId;
        const flowId = flowListEntry.flow.flowId;
        return this.httpApiService.getTimelineBodyFileUrl(clientId, flowId);
      }));

  /**
   * Observable with a filename under which the timeline in the body format
   * should be saved.
   */
  readonly bodyFileName$: Observable<string> =
      this.flowListEntry$.pipe(map(flowListEntry => {
        const clientId = flowListEntry.flow.clientId.replace('C.', '');
        const flowId = flowListEntry.flow.flowId;
        /*
         * TODO(hanuszczak): Chrome does not respect the full file name. It
         * should be invesigated why.
         */
        return `timeline_${clientId}_${flowId}.body`;
      }));
}
