import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {
  FlowFileResult,
  flowFileResultFromStatEntry,
} from '../../../components/flow_details/helpers/file_results_table';
import {
  CollectMultipleFilesArgs,
  StatEntry,
} from '../../../lib/api/api_interfaces';
import {translateStatEntry} from '../../../lib/api_translation/flow';
import {Flow} from '../../../lib/models/flow';
import {PayloadType} from '../../../lib/models/result';
import {
  FlowResultMapFunction,
  FlowResultsQueryWithAdapter,
} from '../helpers/load_flow_results_directive';

import {ExportMenuItem, Plugin} from './plugin';

const ADAPTER: FlowResultMapFunction<readonly FlowFileResult[] | undefined> = (
  results,
) =>
  results?.map((result) =>
    flowFileResultFromStatEntry(
      translateStatEntry(result.payload as StatEntry),
    ),
  );

/**
 * Component that displays results of StatMultipleFiles flow.
 */
@Component({
  selector: 'stat-multiple-files-details',
  templateUrl: './stat_multiple_files_details.ng.html',
  styleUrls: ['./_base.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatMultipleFilesDetails extends Plugin {
  readonly QUERY_MORE_COUNT = 100;

  readonly args$: Observable<CollectMultipleFilesArgs> = this.flow$.pipe(
    map((flow) => flow.args as CollectMultipleFilesArgs),
  );

  readonly flowResultsCount$ = this.flow$.pipe(
    map((flow) => {
      const resultsByType = flow?.resultCounts ?? [];

      const statEntryResultCount = resultsByType.find(
        (count) => count.type === PayloadType.STAT_ENTRY,
      );

      return statEntryResultCount?.count ?? 0;
    }),
  );

  readonly isResultsSectionExpandable$ = this.flowResultsCount$.pipe(
    map((resultsCount) => resultsCount > 0),
  );

  readonly query$: Observable<
    FlowResultsQueryWithAdapter<readonly FlowFileResult[] | undefined>
  > = this.flow$.pipe(map((flow) => ({flow, resultMapper: ADAPTER})));

  readonly description$ = this.args$.pipe(
    map((args) => {
      const length = args.pathExpressions?.length ?? 0;
      if (length <= 1) {
        return args.pathExpressions?.[0] ?? '';
      } else {
        return `${args.pathExpressions?.[0]} + ${length - 1} more`;
      }
    }),
  );

  override getExportMenuItems(flow: Flow): readonly ExportMenuItem[] {
    const downloadItem = this.getDownloadFilesExportMenuItem(flow);
    const items = super.getExportMenuItems(flow);

    if (items.find((item) => item.url === downloadItem.url)) {
      return items;
    }

    // If the menu does not yet contain "Download files", display it.
    return [downloadItem, ...items];
  }
}
