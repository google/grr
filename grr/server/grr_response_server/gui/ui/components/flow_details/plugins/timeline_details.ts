import {Component} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {combineLatest, Observable} from 'rxjs';
import {map, shareReplay, startWith} from 'rxjs/operators';

import {TimelineArgs} from '../../../lib/api/api_interfaces';
import {HttpApiService} from '../../../lib/api/http_api_service';
import {FlowState} from '../../../lib/models/flow';

import {Plugin} from './plugin';

/**
 * Options for customizing the output of exporting timeline in the body format.
 */
declare interface BodyOpts {
  timestampSubsecondPrecision: boolean;
  inodeNtfsFileReferenceFormat: boolean;
  backslashEscape: boolean;
  carriageReturnEscape: boolean;
  nonPrintableEscape: boolean;
}

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

  readonly bodyOptsForm = new FormGroup({
    timestampSubsecondPrecision: new FormControl(true),
    inodeNtfsFileReferenceFormat: new FormControl(false),
    backslashEscape: new FormControl(true),
    carriageReturnEscape: new FormControl(false),
    nonPrintableEscape: new FormControl(false),
  });

  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }

  /**
   * Observable with form inputs of the body export options.
   */
  readonly bodyOpts$: Observable<BodyOpts> =
      this.bodyOptsForm.valueChanges.pipe(
          // TODO(user):
          // Unfortunately, `valueChanges` does not emit the initial value. We
          // work around this with `startWith`.
          startWith(this.bodyOptsForm.value),
          shareReplay(1),
      );

  /** Observable of the state that the flow currently is in. */
  readonly state$: Observable<FlowState> =
      this.flow$.pipe(map(flow => flow.state));

  /** Observable of the arguments that the flow was created with. */
  readonly args$: Observable<TimelineArgs> =
      this.flow$.pipe(map(flow => flow.args as TimelineArgs));

  /**
   * Observable with URL to download the collected timeline in the body format.
   */
  readonly bodyFileUrl$: Observable<URL> = combineLatest([
                                             this.flow$, this.bodyOpts$
                                           ]).pipe(map(([flow, bodyOpts]) => {
    const clientId = flow.clientId;
    const flowId = flow.flowId;
    return this.httpApiService.getTimelineBodyFileUrl(
        clientId, flowId, bodyOpts);
  }));

  /**
   * Observable with a filename under which the timeline in the body format
   * should be saved.
   */
  readonly bodyFileName$: Observable<string> = this.flow$.pipe(map(flow => {
    const clientId = flow.clientId.replace('C.', '');
    const flowId = flow.flowId;
    /*
     * TODO(hanuszczak): Chrome does not respect the full file name. It
     * should be invesigated why.
     */
    return `timeline_${clientId}_${flowId}.body`;
  }));
}
