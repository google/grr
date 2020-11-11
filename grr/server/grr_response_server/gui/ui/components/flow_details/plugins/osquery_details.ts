import { Component, ChangeDetectionStrategy } from '@angular/core';
import { Plugin } from './plugin';
import { map, flatMap, filter, takeUntil, startWith } from 'rxjs/operators';
import { FlowState } from '@app/lib/models/flow';
import { Observable, concat, combineLatest } from 'rxjs';
import { OsqueryResult, OsqueryArgs, OsqueryProgress } from '@app/lib/api/api_interfaces';
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
export class OsqueryDetails extends Plugin {
  private readonly flowError$ = this.flagByState(FlowState.ERROR);
  private readonly flowRunning$ = this.flagByState(FlowState.RUNNING);
  private readonly flowCompleted$ = this.flagByState(FlowState.FINISHED);

  private readonly osqueryResults$: Observable<OsqueryResult> = this.flowListEntry$.pipe(
    flatMap(listEntry => listEntry.resultSets),
    flatMap(singleResultSet => singleResultSet?.items),
    filter(isNonNull),
    map(singleItem => singleItem.payload as OsqueryResult),
  );

  private readonly osqueryProgress$: Observable<OsqueryProgress> = this.flowListEntry$.pipe(
    map(listEntry => listEntry.flow.progress as OsqueryProgress),
    filter(isNonNull),
  );

  private readonly resultsTable$ = this.osqueryResults$.pipe(
    map(result => result.table),
    filter(isNonNull),
  );

  private readonly progressTable$ = this.osqueryProgress$.pipe(
    map(progress => progress.partialTable),
    filter(isNonNull),
  );

  private readonly displayTable$ = concat(
    this.progressTable$.pipe(takeUntil(this.resultsTable$)),
    this.resultsTable$,
  );

  private readonly additionalRowsAvailable$ = combineLatest([
    this.osqueryProgress$.pipe(
      map(progress => progress.totalRowCount),
      startWith(null),
    ),
    this.displayTable$.pipe(
      map(table => table.rows?.length),
      startWith(null),
    ),
  ]).pipe(
    map(([totalRowCount, displayedRowCount]) => {
      if (isNonNull(totalRowCount) && isNonNull(displayedRowCount)) {
        return Number(totalRowCount) - displayedRowCount;
      } else {
        return '?';
      }
    }),
  );

  private readonly args$: Observable<OsqueryArgs> = this.flowListEntry$.pipe(
      map(flowListEntry => flowListEntry.flow.args as OsqueryArgs),
  );

  private readonly resultsStderr$ = this.osqueryResults$.pipe(
    map(result => result.stderr),
  );

  private flagByState(targetState: FlowState): Observable<boolean> {
    return this.flowListEntry$.pipe(
      map(listEntry => listEntry.flow.state === targetState)
    );
  }

  private loadCompleteResults() {
    this.queryFlowResults({offset: 0, count: 1}); // TODO: Fetch more chunks if present
  }
}
