import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {FlowFileResult, flowFileResultFromStatEntry} from '../../../components/flow_details/helpers/file_results_table';
import {FileFinderActionAction, FileFinderArgs, FileFinderResult} from '../../../lib/api/api_interfaces';
import {translateHashToHex, translateStatEntry} from '../../../lib/api_translation/flow';
import {Flow} from '../../../lib/models/flow';
import {FlowResultMapFunction, FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';

import {ExportMenuItem, Plugin} from './plugin';


const ADAPTER: FlowResultMapFunction<ReadonlyArray<FlowFileResult>|undefined> =
    (results) => results?.map(item => item.payload as FileFinderResult)
                     .map(
                         res => flowFileResultFromStatEntry(
                             translateStatEntry(res.statEntry!),
                             translateHashToHex(res.hashEntry ?? {})));

/**
 * Component that shows FileFinder and ClientFileFinder results.
 */
@Component({
  selector: 'file-finder-details',
  templateUrl: './file_table_details.ng.html',
  styleUrls: ['./file_table_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileFinderDetails extends Plugin {
  readonly QUERY_MORE_COUNT = 100;

  readonly args$: Observable<FileFinderArgs> =
      this.flow$.pipe(map((flow) => flow.args as FileFinderArgs));

  readonly totalFileCount$: Observable<number|undefined> = this.flow$.pipe(map(
      (flow) => flow.resultCounts?.find(rc => rc.type === 'FileFinderResult')
                    ?.count));

  readonly query$: Observable<
      FlowResultsQueryWithAdapter<ReadonlyArray<FlowFileResult>|undefined>> =
      this.flow$.pipe(map(flow => ({flow, resultMapper: ADAPTER})));

  readonly description$ = this.args$.pipe(map(args => {
    const length = args.paths?.length ?? 0;
    if (length <= 1) {
      return args.paths?.[0] ?? '';
    } else {
      return `${args.paths?.[0]} + ${length - 1} more`;
    }
  }));

  override getExportMenuItems(flow: Flow): ReadonlyArray<ExportMenuItem> {
    const items = super.getExportMenuItems(flow);

    const args = flow.args as FileFinderArgs;

    // If the flow only collected STAT or HASH, do not show download menu item.
    if (args.action?.actionType !== FileFinderActionAction.DOWNLOAD) {
      return items;
    }

    const downloadItem = this.getDownloadFilesExportMenuItem(flow);

    // If the menu already contains the download menu item, show the menu as is.
    if (items.find(item => item.url === downloadItem.url)) {
      return items;
    }

    // If the menu does not yet contain "Download files", add the menu item.
    return [downloadItem, ...items];
  }
}
