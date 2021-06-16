import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {ArtifactCollectorFlowArgs, ExecuteResponse, StatEntry} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ArtifactCollectorFlowProgress, FlowResult, FlowState} from '@app/lib/models/flow';
import {combineLatest, Observable} from 'rxjs';
import {map, take} from 'rxjs/operators';

import {isRegistryEntry, isStatEntry, translateArtifactCollectorFlowProgress, translateExecuteResponse, translateStatEntry} from '../../../lib/api_translation/flow';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';
import {fromFlowState} from '../helpers/result_accordion';

import {Plugin} from './plugin';


const LOAD_RESULT_COUNT = 100;


function getResults(results: ReadonlyArray<FlowResult>, typeName: 'StatEntry'):
    ReadonlyArray<StatEntry>;
function getResults(
    results: ReadonlyArray<FlowResult>,
    typeName: 'ExecuteResponse'): ReadonlyArray<ExecuteResponse>;
function getResults(
    results: ReadonlyArray<FlowResult>, typeName: string): ReadonlyArray<{}> {
  return results.filter(item => item.payloadType === typeName)
      .map(item => item.payload as {});
}

/** Component that displays flow results. */
@Component({
  selector: 'artifact-collector-flow-details',
  templateUrl: './artifact_collector_flow_details.ng.html',
  styleUrls: ['./artifact_collector_flow_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FlowResultsLocalStore],
})
export class ArtifactCollectorFlowDetails extends Plugin implements OnInit {
  readonly FINISHED = FlowState.FINISHED;

  readonly flowState$: Observable<FlowState> = this.flow$.pipe(
      map((flow) => flow.state),
  );

  readonly progress$: Observable<ArtifactCollectorFlowProgress> =
      this.flow$.pipe(map(translateArtifactCollectorFlowProgress));

  readonly archiveUrl$: Observable<string> = this.flow$.pipe(map((flow) => {
    return this.httpApiService.getFlowFilesArchiveUrl(
        flow.clientId, flow.flowId);
  }));

  readonly archiveFileName$: Observable<string> =
      this.flow$.pipe(map((flow) => {
        return flow.clientId.replace('.', '_') + '_' + flow.flowId + '.zip';
      }));

  private readonly results$ = this.flowResultGlobalStore.results$.pipe(
      map(rs => rs?.map(item => item.payload) ?? []));

  readonly totalResults$: Observable<number|undefined> =
      this.progress$.pipe(map(progress => {
        if (progress.artifacts.size === 0) {
          return undefined;
        }

        return Array.from(progress.artifacts.values())
            .reduce<number|undefined>((totalResults, {numResults}) => {
              if (numResults === undefined || totalResults === undefined) {
                return undefined;
              } else {
                return totalResults + numResults;
              }
            }, 0);
      }));

  readonly totalLoadedResults$ =
      this.results$.pipe(map(results => results.length));

  private readonly statEntryResults$ = this.flowResultGlobalStore.results$.pipe(
      map((results) =>
              getResults(results ?? [], 'StatEntry').map(translateStatEntry)));

  readonly fileResults$ = this.statEntryResults$.pipe(
      map((results) => results.filter(isStatEntry)
                           .map(stat => flowFileResultFromStatEntry(stat))),
  );

  readonly totalFileResults$ =
      this.fileResults$.pipe(map(results => results.length));

  readonly registryResults$ = this.statEntryResults$.pipe(
      map((results) => results.filter(isRegistryEntry)),
  );

  readonly totalRegistryResults$ =
      this.registryResults$.pipe(map(results => results.length));

  readonly executeResponseResults$ = this.flowResultGlobalStore.results$.pipe(
      map((results) => getResults(results ?? [], 'ExecuteResponse')
                           .map(translateExecuteResponse)),
  );

  readonly totalExecuteResponseResults$ =
      this.executeResponseResults$.pipe(map(results => results.length));

  readonly totalResultsRequested$ =
      this.flowResultGlobalStore.query$.pipe(map(query => query?.count ?? 0));

  readonly expandable$ = this.totalResults$.pipe(
      map(totalResults => totalResults === undefined || totalResults > 0),
  );

  readonly description$ = this.totalResults$.pipe(map(totalResults => {
    if (totalResults === undefined) {
      return '';
    } else if (totalResults === 1) {
      return '1 result';
    } else {
      return `${totalResults} results`;
    }
  }));

  readonly status$ = this.flow$.pipe(map(flow => fromFlowState(flow.state)));

  readonly totalUnknownResults$ =
      combineLatest([
        this.totalLoadedResults$,
        this.totalFileResults$,
        this.totalExecuteResponseResults$,
      ]).pipe(map(([total, file, execute]) => total - file - execute));

  readonly flowArgs$: Observable<ArtifactCollectorFlowArgs> =
      this.flow$.pipe(map(flow => flow.args as ArtifactCollectorFlowArgs));

  constructor(
      private readonly httpApiService: HttpApiService,
      private readonly flowResultGlobalStore: FlowResultsLocalStore) {
    super();
  }

  ngOnInit() {
    this.flowResultGlobalStore.query(this.flow$.pipe(
        take(1),
        map(flow => ({flow})),
        ));
  }

  loadMoreResults() {
    this.flowResultGlobalStore.queryMore(LOAD_RESULT_COUNT);
  }
}
