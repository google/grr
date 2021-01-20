import {AfterViewInit, ChangeDetectionStrategy, Component} from '@angular/core';
import {flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {AnyObject, StatEntry} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {FlowState} from '@app/lib/models/flow';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {Plugin} from './plugin';


function isStatEntry(payload: unknown): payload is StatEntry {
  return (payload as AnyObject)['stSize'] !== undefined;
}

/** Component that displays flow results. */
@Component({
  selector: 'artifact-collector-flow-details',
  templateUrl: './artifact_collector_flow_details.ng.html',
  styleUrls: ['./artifact_collector_flow_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactCollectorFlowDetails extends Plugin implements
    AfterViewInit {
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

  readonly fileResults$ = this.results$.pipe(
      map((results) => results.filter(isStatEntry)
                           .map(stat => flowFileResultFromStatEntry(stat))),
  );

  readonly totalFileResults$ =
      this.fileResults$.pipe(map(results => results.length));

  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }

  ngAfterViewInit() {
    this.queryFlowResults({
      offset: 0,
      count: 10,
    });
  }
}
