import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {filter, map} from 'rxjs/operators';

import {ExecuteBinaryResponse, LaunchBinaryArgs} from '../../../lib/api/api_interfaces';
import {translateExecuteBinaryResponse} from '../../../lib/api_translation/flow';
import {isNonNull} from '../../../lib/preconditions';
import {FlowResultsLocalStore} from '../../../store/flow_results_local_store';

import {Plugin} from './plugin';


/** Details and results of LaunchBinary flow. */
@Component({
  templateUrl: './launch_binary_details.ng.html',
  styleUrls: ['./launch_binary_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LaunchBinaryDetails extends Plugin {
  constructor(
      private readonly flowResultsLocalStore: FlowResultsLocalStore,
  ) {
    super();

    this.flowResultsLocalStore.query(this.flow$.pipe(
        map(flow => ({flow, withType: 'ExecuteBinaryResponse'}))));
  }

  readonly args$: Observable<LaunchBinaryArgs> = this.flow$.pipe(
      map((flow) => flow.args as LaunchBinaryArgs),
  );

  readonly title$ =
      this.args$.pipe(map(args => `${args.binary} ${args.commandLine}`));

  readonly result$ = this.flowResultsLocalStore.results$.pipe(
      map(results => results[0]?.payload as ExecuteBinaryResponse | undefined),
      filter(isNonNull),
      map(translateExecuteBinaryResponse),
  );

  // Emit `null` if stderr is the empty string "" to hide this section in the
  // UI.
  readonly stderr$ = this.result$.pipe(
      map(result => result.stderr ? result.stderr.split('\n') : null),
  );

  // Emit [] if stdout is the empty string "" to always show this section in
  // the UI.
  readonly stdout$ = this.result$.pipe(
      map(result => result.stdout?.split('\n') ?? []),
  );

  readonly hasResults$ = this.flow$.pipe(
      map(flow => !!(flow.resultCounts?.[0]?.count)),
  );

  loadResults() {
    this.flowResultsLocalStore.queryMore(1);
  }
}
