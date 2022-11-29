import {TimelineArgs} from '../api/api_interfaces';
import {getTimelineBodyFileUrl} from '../api/http_api_service';
import {Flow} from '../models/flow';

import {ExportMenuItem, FlowDetailsAdapter} from './adapter';

/** Adapter for Timeline flow. */
export class TimelineAdapter extends FlowDetailsAdapter<Flow<TimelineArgs>> {
  override getExportMenuItems(flow: Flow<TimelineArgs>):
      readonly ExportMenuItem[] {
    return [
      {
        title: 'Download body file',
        downloadName: `timeline_${flow.clientId}_${flow.flowId}.body`,
        url: getTimelineBodyFileUrl(flow.clientId, flow.flowId, {
          timestampSubsecondPrecision: true,
          inodeNtfsFileReferenceFormat: false,
          backslashEscape: true,
          carriageReturnEscape: true,
          nonPrintableEscape: true,
        })
      },
      {
        title: 'Download body file (Windows format)',
        downloadName: `timeline_${flow.clientId}_${flow.flowId}.body`,
        url: getTimelineBodyFileUrl(flow.clientId, flow.flowId, {
          timestampSubsecondPrecision: true,
          inodeNtfsFileReferenceFormat: true,
          backslashEscape: true,
          carriageReturnEscape: true,
          nonPrintableEscape: true,
        })
      }
    ];
  }
}
