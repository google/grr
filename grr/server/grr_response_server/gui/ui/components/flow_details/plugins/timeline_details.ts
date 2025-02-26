import {Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {TimelineArgs} from '../../../lib/api/api_interfaces';
import {getTimelineBodyFileUrl} from '../../../lib/api/http_api_service';
import {decodeBase64ToString} from '../../../lib/api_translation/primitive';
import {Flow, FlowState} from '../../../lib/models/flow';

import {ButtonType, ExportMenuItem, Plugin} from './plugin';

/**
 * A component with the details about the timeline flow.
 *
 * The timeline flow recursively collects metadata about all files in the file-
 * system (or a specified directory).
 */
@Component({
  standalone: false,
  selector: 'timeline-details',
  templateUrl: './timeline_details.ng.html',
  styleUrls: ['./timeline_details.scss'],
})
export class TimelineDetails extends Plugin {
  readonly FlowState: typeof FlowState = FlowState;

  /** Observable of the arguments that the flow was created with. */
  readonly args$: Observable<TimelineArgs> = this.flow$.pipe(
    map((flow) => flow.args as TimelineArgs),
  );

  readonly root$ = this.args$.pipe(
    map((args) => (args.root ? decodeBase64ToString(args.root) : null)),
  );

  override getExportMenuItems(flow: Flow): readonly ExportMenuItem[] {
    return [
      {
        title: 'Download body file',
        url: getTimelineBodyFileUrl(flow.clientId, flow.flowId, {
          timestampSubsecondPrecision: true,
          inodeNtfsFileReferenceFormat: false,
          backslashEscape: true,
          carriageReturnEscape: true,
          nonPrintableEscape: true,
        }),
        type: ButtonType.LINK,
      },
      {
        title: 'Download body file (Windows format)',
        url: getTimelineBodyFileUrl(flow.clientId, flow.flowId, {
          timestampSubsecondPrecision: true,
          inodeNtfsFileReferenceFormat: true,
          backslashEscape: true,
          carriageReturnEscape: true,
          nonPrintableEscape: true,
        }),
        type: ButtonType.LINK,
      },
    ];
  }
}
