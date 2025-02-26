import {ChangeDetectionStrategy, Component, inject} from '@angular/core';
import {Observable} from 'rxjs';
import {map, takeUntil} from 'rxjs/operators';

import {ListProcessesArgs, Process} from '../../../lib/api/api_interfaces';
import {FlowResult} from '../../../lib/models/flow';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {Plugin} from './plugin';

const INITIAL_RESULT_COUNT = 1000;

function asProcess(data: FlowResult): Process {
  const process = data.payload as Process;

  if (process.pid === undefined) {
    throw new Error(`"Expected Process with pid, received ${data}.`);
  }
  return process;
}

/**
 * Component that displays ListProcesses flow results.
 */
@Component({
  standalone: false,
  selector: 'list_processes-flow-details',
  templateUrl: './list_processes_details.ng.html',
  styleUrls: ['./list_processes_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListProcessesDetails extends Plugin {
  readonly flowResultsLocalStore = inject(FlowResultsLocalStore);
  readonly processes$ = new Observable<Process[]>();

  constructor() {
    super();

    this.flowResultsLocalStore.query(
      this.flow$.pipe(map((flow) => ({flow, withType: 'Process'}))),
    );

    this.processes$ = this.flowResultsLocalStore.results$.pipe(
      map((results) => results.map(asProcess)),
      takeUntil(this.ngOnDestroy.triggered$),
    );
  }

  private readonly flowArgs$ = this.flow$.pipe(
    map((flow) => flow.args as ListProcessesArgs),
  );

  readonly title$ = this.flowArgs$.pipe(
    map((args) => {
      const conditions: string[] = [];

      if (args.pids?.length) {
        conditions.push(`PID matching ${args.pids.join(', ')}`);
      }
      if (args.filenameRegex) {
        conditions.push(`executable matching ${args.filenameRegex}`);
      }
      if (args.connectionStates?.length) {
        conditions.push(`connections in ${args.connectionStates.join(', ')}`);
      }
      if (conditions.length) {
        return capitalize(conditions.join(' and '));
      } else {
        return 'All processes';
      }
    }),
  );

  onShowClicked() {
    this.flowResultsLocalStore.queryMore(INITIAL_RESULT_COUNT);
  }
}

function capitalize(v: string): string {
  return v[0].toUpperCase() + v.slice(1);
}
