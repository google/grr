import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {filter, map} from 'rxjs/operators';

import {ExecutePythonHackArgs, ExecutePythonHackResult} from '../../../lib/api/api_interfaces';
import {translateDict} from '../../../lib/api_translation/primitive';
import {isNonNull} from '../../../lib/preconditions';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {Plugin} from './plugin';


/** Details and results of ExecutePythonHack flow. */
@Component({
  templateUrl: './execute_python_hack_details.ng.html',
  styleUrls: ['./execute_python_hack_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExecutePythonHackDetails extends Plugin {
  constructor(
      private readonly flowResultsLocalStore: FlowResultsLocalStore,
  ) {
    super();

    this.flowResultsLocalStore.query(this.flow$.pipe(
        map(flow => ({flow, withType: 'ExecutePythonHackResult'}))));
  }

  readonly args$: Observable<ExecutePythonHackArgs> = this.flow$.pipe(
      map((flow) => flow.args as ExecutePythonHackArgs),
  );

  readonly title$ = this.args$.pipe(map(args => {
    const pyArgs = Array.from(translateDict(args.pyArgs ?? {}).entries())
                       .map(([k, v]) => `${k}=${v}`)
                       .join(' ');
    return `${args.hackName} ${pyArgs}`;
  }));

  readonly textContent$ = this.flowResultsLocalStore.results$.pipe(
      map(results =>
              (results[0]?.payload as(ExecutePythonHackResult | undefined))
                  ?.resultString?.split('\n')),
      filter(isNonNull),
  );

  readonly hasResults$ = this.flow$.pipe(
      map(flow => !!(flow.resultCounts?.[0]?.count)),
  );

  loadResults() {
    this.flowResultsLocalStore.queryMore(1);
  }
}
