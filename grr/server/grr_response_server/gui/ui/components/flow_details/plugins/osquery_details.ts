import { Component, ChangeDetectionStrategy, OnInit, OnDestroy } from '@angular/core';
import {Plugin} from './plugin';
import { map, tap, flatMap, takeUntil } from 'rxjs/operators';
import { FlowState, FlowResultSet, FlowResult } from '@app/lib/models/flow';
import { Observable, Subject, from } from 'rxjs';
import { OsqueryResult, OsqueryTable } from '@app/lib/api/api_interfaces';

/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'osquery-details',
  templateUrl: './osquery_details.ng.html',
  styleUrls: ['./osquery_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryDetails extends Plugin implements OnDestroy {
  private readonly unsubscribe$ = new Subject<void>();

  hasLoadedResults = false;

  flowRunning$ = this.flagTargetState(FlowState.RUNNING);
  flowCompleted$ = this.flagTargetState(FlowState.FINISHED);
  flowError$ = this.flagTargetState(FlowState.ERROR);

  osqueryResult$: Observable<OsqueryResult> = this.flowListEntry$.pipe(
    flatMap((listEntry) => listEntry.resultSets),
    flatMap((singleResult) => singleResult?.items),
    map((singleResultItem) => singleResultItem?.payload as OsqueryResult)
  );

  resultTable$ = this.osqueryResult$.pipe(
    map((result) => result?.table),
  );

  resultStderr$ = this.osqueryResult$.pipe(
    map((result) => result?.stderr)
  );

  constructor() {
    super();

    this.autocloseSubscription(this.flowCompleted$)
      .subscribe((completed) => {
        if (completed) {
          this.loadResults();
        }
    })
  }

  flagTargetState(targetState: FlowState): Observable<boolean> {
    return this.flowListEntry$.pipe(
      map((listEntry) => listEntry.flow.state === targetState)
    );
  }

  autocloseSubscription(o: Observable<any>) {
    return o.pipe(takeUntil(this.unsubscribe$));
  }

  loadResults() {
    if (!this.hasLoadedResults) {
      super.queryFlowResults({offset: 0, count: 1});
      this.hasLoadedResults = true;
      console.log('Flow completed, loading results')
    }
  }

  buttonClicked() {
    console.log('Button clicked!');
    super.queryFlowResults({offset: 0, count: 1});
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
