import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FlowFileResult, flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {CollectMultipleFilesArgs, CollectMultipleFilesProgress, CollectMultipleFilesResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {FlowState} from '@app/lib/models/flow';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {translateHashToHex} from '../../../lib/api_translation/flow';
import {FlowResultMapFunction, FlowResultsQueryWithAdapter} from '../helpers/load_flow_results_directive';

import {Plugin} from './plugin';


const ADAPTER: FlowResultMapFunction<ReadonlyArray<FlowFileResult>|undefined> =
    (results) =>
        results?.map(item => item.payload as CollectMultipleFilesResult)
            .map(
                res => flowFileResultFromStatEntry(
                    res.stat!, translateHashToHex(res.hash ?? {})));


/**
 * Component that displays results of CollectMultipleFiles flow.
 */
@Component({
  selector: 'collect-multiple-files-details',
  templateUrl: './collect_multiple_files_details.ng.html',
  styleUrls: ['./collect_multiple_files_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectMultipleFilesDetails extends Plugin {
  readonly QUERY_MORE_COUNT = 100;

  readonly FINISHED = FlowState.FINISHED;

  readonly hasProgress$: Observable<boolean> = this.flow$.pipe(
      map((flow) => flow.progress !== undefined),
  );

  readonly args$: Observable<CollectMultipleFilesArgs> = this.flow$.pipe(
      map((flow) => flow.args as CollectMultipleFilesArgs),
  );

  readonly flowState$: Observable<FlowState> = this.flow$.pipe(
      map((flow) => flow.state),
  );

  readonly flowProgress$: Observable<CollectMultipleFilesProgress> =
      this.flow$.pipe(
          map((flow) => flow.progress as CollectMultipleFilesProgress),
      );

  readonly totalFiles$: Observable<number> = this.flowProgress$.pipe(
      map((progress) => Number(progress?.numCollected ?? 0)));

  readonly archiveUrl$: Observable<string> = this.flow$.pipe(map((flow) => {
    return this.httpApiService.getFlowFilesArchiveUrl(
        flow.clientId, flow.flowId);
  }));

  readonly archiveFileName$: Observable<string> =
      this.flow$.pipe(map((flow) => {
        return flow.clientId.replace('.', '_') + '_' + flow.flowId + '.zip';
      }));

  readonly query$: Observable<
      FlowResultsQueryWithAdapter<ReadonlyArray<FlowFileResult>|undefined>> =
      this.flow$.pipe(map(flow => ({flow, adapter: ADAPTER})));

  readonly description$ = this.args$.pipe(map(args => {
    const length = args.pathExpressions?.length ?? 0;
    if (length <= 1) {
      return args.pathExpressions?.[0] ?? '';
    } else {
      return `${args.pathExpressions?.[0]} + ${length - 1} more`;
    }
  }));

  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }
}
