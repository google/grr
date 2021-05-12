import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {ArtifactCollectorFlowArgs, ExecuteResponse, StatEntry} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {FlowListEntry, FlowState} from '@app/lib/models/flow';
import {combineLatest, Observable, ReplaySubject} from 'rxjs';
import {distinctUntilChanged, map, scan, startWith, takeUntil} from 'rxjs/operators';

import {translateExecuteResponse} from '../../../lib/api_translation/flow';

import {Plugin} from './plugin';


const LOAD_RESULT_COUNT = 100;


function getResults(
    fle: FlowListEntry, typeName: 'StatEntry'): ReadonlyArray<StatEntry>;
function getResults(fle: FlowListEntry, typeName: 'ExecuteResponse'):
    ReadonlyArray<ExecuteResponse>;
function getResults(fle: FlowListEntry, typeName: string): ReadonlyArray<{}> {
  return fle.resultSets.flatMap(rs => rs.items)
      .filter(item => item.payloadType === typeName)
      .map(item => item.payload as {});
}


/** Component that displays flow results. */
@Component({
  selector: 'artifact-collector-flow-details',
  templateUrl: './artifact_collector_flow_details.ng.html',
  styleUrls: ['./artifact_collector_flow_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactCollectorFlowDetails extends Plugin implements OnInit {
  readonly FINISHED = FlowState.FINISHED;

  readonly flowState$: Observable<FlowState> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.state),
  );

  readonly archiveUrl$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return this.httpApiService.getFlowFilesArchiveUrl(
            flowListEntry.flow.clientId, flowListEntry.flow.flowId);
      }));

  readonly archiveFileName$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return flowListEntry.flow.clientId.replace('.', '_') + '_' +
            flowListEntry.flow.flowId + '.zip';
      }));

  private readonly results$ = this.flowListEntry$.pipe(
      map(flowListEntry => flowListEntry.resultSets.flatMap(
              rs => rs.items.map(item => item.payload))));

  readonly totalResults$ = this.results$.pipe(map(results => results.length));

  readonly fileResults$ = this.flowListEntry$.pipe(
      map((fle) => getResults(fle, 'StatEntry')
                       .map(stat => flowFileResultFromStatEntry(stat))),
  );

  readonly totalFileResults$ =
      this.fileResults$.pipe(map(results => results.length));

  readonly executeResponseResults$ = this.flowListEntry$.pipe(
      map((fle) =>
              getResults(fle, 'ExecuteResponse').map(translateExecuteResponse)),
  );

  readonly totalExecuteResponseResults$ =
      this.executeResponseResults$.pipe(map(results => results.length));

  private readonly resultsRequested$ = new ReplaySubject<number>(1);

  readonly totalResultsRequested$ = this.resultsRequested$.pipe(
      startWith(0),
      scan((acc, cur) => acc + cur),
  );

  readonly hasMoreResults$ =
      combineLatest([this.totalResultsRequested$, this.totalResults$])
          .pipe(
              map(([requested, loaded]) => requested <= loaded),
              startWith(true),
          );

  readonly totalUnknownResults$ =
      combineLatest([
        this.totalResults$,
        this.totalFileResults$,
        this.totalExecuteResponseResults$,
      ]).pipe(map(([total, file, execute]) => total - file - execute));

  readonly flowArgs$: Observable<ArtifactCollectorFlowArgs> =
      this.flowListEntry$.pipe(
          map(fle => fle.flow.args as ArtifactCollectorFlowArgs));

  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }

  ngOnInit() {
    combineLatest([
      this.totalResultsRequested$,
      this.totalResults$.pipe(distinctUntilChanged()),
    ])
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(([resultsRequested, resultsLoaded]) => {
          if (resultsRequested > resultsLoaded) {
            this.queryFlowResults({
              offset: 0,
              count: resultsRequested,
            });
          }
        });
  }

  loadMoreResults() {
    this.resultsRequested$.next(LOAD_RESULT_COUNT);
  }
}
