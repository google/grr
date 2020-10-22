import { Component, ChangeDetectionStrategy, OnInit, OnDestroy } from '@angular/core';
import {Plugin} from './plugin';
import { map, tap, flatMap, takeUntil, filter } from 'rxjs/operators';
import { FlowState, FlowResultSet, FlowResult, FlowListEntry } from '@app/lib/models/flow';
import { Observable, Subject, from } from 'rxjs';
import { OsqueryResult, OsqueryArgs } from '@app/lib/api/api_interfaces';

/**
 * Component that displays the details (status, errors, results) for a particular Osquery Flow.
 */
@Component({
  selector: 'osquery-details',
  templateUrl: './osquery_details.ng.html',
  styleUrls: ['./osquery_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryDetails extends Plugin implements OnDestroy {
  private readonly onDestroyHappened$ = new Subject<void>();

  hasLoadedResults = false;

  flowRunning$ = this.flagByState(FlowState.RUNNING);
  flowCompleted$ = this.flagByState(FlowState.FINISHED);
  flowError$ = this.flagByState(FlowState.ERROR);

  args$: Observable<OsqueryArgs> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.args as OsqueryArgs)
  );

  osqueryResult$: Observable<OsqueryResult> = this.flowListEntry$.pipe(
    flatMap((listEntry) => listEntry.resultSets),
    flatMap((singleResultSet) => singleResultSet?.items),
    map((singleItem) => singleItem?.payload as OsqueryResult)
  );

  resultTable$ = this.osqueryResult$.pipe(
    map((result) => result?.table),
  );

  resultStderr$ = this.osqueryResult$.pipe(
    map((result) => result?.stderr)
  );

  flagByState(targetState: FlowState): Observable<boolean> {
    return this.flowListEntry$.pipe(
      map((listEntry) => listEntry.flow.state === targetState)
    );
  }

  constructor() {
    super();
    this.completeOnDestroy(this.flowCompleted$)
      .subscribe(() => this.loadResults());
  }

  completeOnDestroy<T>(obs: Observable<T>): Observable<T> {
    return obs.pipe(takeUntil(this.onDestroyHappened$));
  }

  loadResults() {
    if (!this.hasLoadedResults) {
      this.queryFlowResults({offset: 0, count: 1});
      this.hasLoadedResults = true;
    }
  }

  ngOnDestroy() {
    this.onDestroyHappened$.next();
    this.onDestroyHappened$.complete();
  }
}
