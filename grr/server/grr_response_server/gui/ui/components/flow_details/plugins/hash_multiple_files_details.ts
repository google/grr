import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {
  FlowFileResult,
  flowFileResultFromStatEntry,
} from '../../../components/flow_details/helpers/file_results_table';
import {
  CollectMultipleFilesArgs,
  CollectMultipleFilesResult,
  HashMultipleFilesProgress,
} from '../../../lib/api/api_interfaces';
import {
  translateHashToHex,
  translateStatEntry,
} from '../../../lib/api_translation/flow';
import {Flow} from '../../../lib/models/flow';
import {
  FlowResultMapFunction,
  FlowResultsQueryWithAdapter,
} from '../helpers/load_flow_results_directive';

import {ExportMenuItem, Plugin} from './plugin';

const ADAPTER: FlowResultMapFunction<readonly FlowFileResult[] | undefined> = (
  results,
) =>
  results
    ?.map((item) => item.payload as CollectMultipleFilesResult)
    .map((res) =>
      flowFileResultFromStatEntry(
        translateStatEntry(res.stat!),
        translateHashToHex(res.hash ?? {}),
      ),
    );

/**
 * Component that displays results of CollectMultipleFiles flow.
 */
@Component({
  standalone: false,
  selector: 'hash-multiple-files-details',
  templateUrl: './hash_multiple_files_details.ng.html',
  styleUrls: ['./_base.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HashMultipleFilesDetails extends Plugin {
  readonly QUERY_MORE_COUNT = 100;

  readonly args$: Observable<CollectMultipleFilesArgs> = this.flow$.pipe(
    map((flow) => flow.args as CollectMultipleFilesArgs),
  );

  readonly flowProgress$: Observable<HashMultipleFilesProgress> =
    this.flow$.pipe(map((flow) => flow.progress as HashMultipleFilesProgress));

  readonly totalFiles$: Observable<number> = this.flowProgress$.pipe(
    map((progress) => Number(progress?.numHashed ?? 0)),
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

  override getExportMenuItems(
    flow: Flow,
    exportCommandPrefix: string,
  ): readonly ExportMenuItem[] {
    const items = super.getExportMenuItems(flow, exportCommandPrefix);
    const downloadItem = this.getDownloadFilesExportMenuItem(flow);

    if (items.find((item) => item.url === downloadItem.url)) {
      return items;
    }

    // If the menu does not yet contain "Download files", display it.
    return [downloadItem, ...items];
  }
}
