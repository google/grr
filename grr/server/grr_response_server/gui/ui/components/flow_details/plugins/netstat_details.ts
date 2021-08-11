import {ChangeDetectionStrategy, Component} from '@angular/core';
import {isNonNull} from '@app/lib/preconditions';
import {Observable} from 'rxjs';
import {filter, map} from 'rxjs/operators';

import {NetstatArgs, NetworkConnection} from '../../../lib/api/api_interfaces';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {Plugin} from './plugin';

const INITIAL_RESULT_COUNT = 1000;

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
  readonly columns: string[] = [
    'PID', 'Process Name', 'State', 'Type', 'Family', 'Local IP', 'Local Port',
    'Remote IP', 'Remote Port'
  ];

  readonly netstatResults$: Observable<NetworkConnection[]> =
      this.flowResultsLocalStore.results$.pipe(
          map(results =>
                  results?.map((data) => data.payload as NetworkConnection)),
          filter(isNonNull));

  constructor(
      private readonly flowResultsLocalStore: FlowResultsLocalStore,
  ) {
    super();
    this.flowResultsLocalStore.query(
        this.flow$.pipe(map(flow => ({flow, withType: 'NetworkConnection'}))));
  }

  private readonly flowArgs$ =
      this.flow$.pipe(map(flow => flow.args as NetstatArgs));

  readonly title$ = this.flowArgs$.pipe(map(args => {
    if (args.listeningOnly) {
      return 'Listening Only';
    } else {
      return 'All connections';
    }
  }));

  onShowClicked() {
    this.flowResultsLocalStore.queryMore(INITIAL_RESULT_COUNT);
  }
}
