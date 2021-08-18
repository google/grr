import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FlowState} from '@app/lib/models/flow';
import {Observable, of} from 'rxjs';
import {map} from 'rxjs/operators';

import {NetstatArgs, NetworkConnection} from '../../../lib/api/api_interfaces';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {Plugin} from './plugin';

const INITIAL_RESULT_COUNT = 1000;

const COLUMNS: ReadonlyArray<string> = [
  'pid',
  'processName',
  'state',
  'type',
  'family',
  'localIP',
  'localPort',
  'remoteIP',
  'remotePort',
];

/**
 * Component that displays the details (results) for a
 * particular Netstat Flow.
 */
@Component({
  selector: 'netstat-details',
  templateUrl: './netstat_details.ng.html',
  styleUrls: ['./netstat_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NetstatDetails extends Plugin {
  constructor(
      private readonly flowResultsLocalStore: FlowResultsLocalStore,
  ) {
    super();
    this.flowResultsLocalStore.query(
        this.flow$.pipe(map(flow => ({flow, withType: 'NetworkConnection'}))));
  }

  displayedColumns$: Observable<ReadonlyArray<string>> = of(COLUMNS);

  readonly netstatResults$: Observable<NetworkConnection[]> =
      this.flowResultsLocalStore.results$.pipe(
          map(results =>
                  results?.map((data) => data.payload as NetworkConnection)));

  readonly FINISHED = FlowState.FINISHED;

  readonly flowState$: Observable<FlowState> = this.flow$.pipe(
      map((flow) => flow.state),
  );

  private readonly flowArgs$ =
      this.flow$.pipe(map(flow => flow.args as NetstatArgs));

  readonly title$ = this.flowArgs$.pipe(map(args => {
    if (args.listeningOnly) {
      return 'Listening only';
    } else {
      return 'All connections';
    }
  }));

  onShowClicked() {
    this.flowResultsLocalStore.queryMore(INITIAL_RESULT_COUNT);
  }

  trackByConnectionRowIndex(index: number, item: NetworkConnection) {
    return index;
  }
}
