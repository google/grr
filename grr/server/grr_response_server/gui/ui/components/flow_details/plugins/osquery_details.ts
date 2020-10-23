import { Component, ChangeDetectionStrategy, OnDestroy } from '@angular/core';
import { Plugin } from './plugin';
import { map, flatMap, takeUntil, filter, take } from 'rxjs/operators';
import { FlowState } from '@app/lib/models/flow';
import { Observable, Subject } from 'rxjs';
import { OsqueryResult, OsqueryArgs, OsqueryColumn, OsqueryRow } from '@app/lib/api/api_interfaces';
import { isNonNull } from '@app/lib/preconditions';

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
  readonly unsubscribe$ = new Subject<void>();

  readonly flowRunning$ = this.flagByState(FlowState.RUNNING);
  readonly flowCompleted$ = this.flagByState(FlowState.FINISHED);
  readonly flowError$ = this.flagByState(FlowState.ERROR);

  readonly args$: Observable<OsqueryArgs> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.args as OsqueryArgs)
  );

  readonly osqueryResult$: Observable<OsqueryResult> = this.flowListEntry$.pipe(
    flatMap((listEntry) => listEntry.resultSets),
    flatMap((singleResultSet) => singleResultSet?.items),
    filter(isNonNull),
    map((singleItem) => singleItem?.payload as OsqueryResult)
  );

  readonly resultTable$ = this.osqueryResult$.pipe(
    map((result) => result?.table),
  );

  readonly resultStderr$ = this.osqueryResult$.pipe(
    map((result) => result?.stderr)
  );

  private flagByState(targetState: FlowState): Observable<boolean> {
    return this.flowListEntry$.pipe(
      map((listEntry) => listEntry.flow.state === targetState)
    );
  }

  constructor() {
    super();
    this.flowCompleted$
      .pipe(
        takeUntil(this.unsubscribe$),
        filter(completed => completed),
        take(1))
      .subscribe(() => this.loadResults());
  }

  private loadResults() {
    this.queryFlowResults({offset: 0, count: 1});
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }

  trackColumnByName(index: number, column: OsqueryColumn) {
    return column.name;
  }

  trackCellByValue(index: number, cell: string) {
    return cell;
  }

  trackRowByContents(index: number, row: OsqueryRow) {
    return row.values?.join();
  }
}
