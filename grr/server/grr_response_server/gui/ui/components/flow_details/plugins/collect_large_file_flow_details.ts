import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {
  CollectLargeFileFlowArgs,
  CollectLargeFileFlowProgress,
  CollectLargeFileFlowResult,
} from '../../../lib/api/api_interfaces';
import {Flow} from '../../../lib/models/flow';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {ButtonType, ExportMenuItem, Plugin} from './plugin';

/**
 * Component that shows Download for CollectLargeFilesFlow results.
 */
@Component({
  standalone: false,
  selector: 'collect-large-file-flow-details',
  templateUrl: './collect_large_file_flow_details.ng.html',
  styleUrls: ['./collect_large_file_flow_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectLargeFileFlowDetails extends Plugin {
  private readonly flowResultsLocalStore = inject(FlowResultsLocalStore);

  constructor() {
    super();
    this.flowResultsLocalStore.query(
      this.flow$.pipe(
        map((flow) => ({flow, withType: 'CollectLargeFileFlowResult'})),
      ),
    );
  }

  readonly largeFilePath$ = this.flow$.pipe(
    map((flow) => (flow.args as CollectLargeFileFlowArgs)?.pathSpec?.path),
  );

  loadResult() {
    this.flowResultsLocalStore.queryMore(1);
  }

  readonly flowProgress$: Observable<CollectLargeFileFlowProgress> =
    this.flow$.pipe(
      map((flow) => flow.progress as CollectLargeFileFlowProgress),
    );

  readonly hasProgress$: Observable<boolean> = this.flowProgress$.pipe(
    map((progress) => (progress?.sessionUri ? true : false)),
  );

  readonly largeFileResult$: Observable<
    CollectLargeFileFlowResult | undefined
  > = this.flowResultsLocalStore.results$.pipe(
    map((results) => {
      if ((results ?? []).length > 0) {
        return results[0].payload as CollectLargeFileFlowResult;
      }
      return undefined;
    }),
  );

  readonly hasResult$ = this.flow$.pipe(
    map(
      (flow) =>
        flow.resultCounts?.find(
          (resultCount) => resultCount.type === 'CollectLargeFileFlowResult',
        )?.count ?? 0 > 0,
    ),
  );

  readonly parseInt = parseInt;

  override getExportMenuItems(
    flow: Flow<CollectLargeFileFlowArgs>,
    exportCommandPrefix: string,
  ): readonly ExportMenuItem[] {
    if (flow.args?.signedUrl) {
      return [
        {
          title: 'Download Encrypted File',
          url: flow.args?.signedUrl,
          type: ButtonType.LINK,
        },
      ];
    }
    return [];
  }
}
