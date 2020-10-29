import { Component, ChangeDetectionStrategy, OnDestroy } from '@angular/core';
import { Plugin } from './plugin';
import { map, flatMap, takeUntil, filter, take } from 'rxjs/operators';
import { FlowState } from '@app/lib/models/flow';
import { Observable, Subject } from 'rxjs';
import { OsqueryResult, OsqueryArgs, OsqueryColumn, OsqueryRow, OsqueryProgress } from '@app/lib/api/api_interfaces';
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
  readonly flowRunning$ = this.flagByState(FlowState.RUNNING);
  readonly flowCompleted$ = this.flagByState(FlowState.FINISHED);
  readonly flowError$ = this.flagByState(FlowState.ERROR);

  readonly args$: Observable<OsqueryArgs> = this.flowListEntry$.pipe(
      map(flowListEntry => flowListEntry.flow.args as OsqueryArgs)
  );

  readonly osqueryResult$: Observable<OsqueryResult> = this.flowListEntry$.pipe(
    flatMap(listEntry => listEntry.resultSets),
    flatMap(singleResultSet => singleResultSet?.items),
    filter(isNonNull),
    map(singleItem => singleItem.payload as OsqueryResult),
  );

  readonly resultTable$ = this.osqueryResult$.pipe(
    map(result => result?.table),
  );

  readonly resultStderr$ = this.osqueryResult$.pipe(
    map(result => result?.stderr)
  );

  readonly osqueryProgress$: Observable<OsqueryProgress> = this.flowListEntry$.pipe(
    map(listEntry => listEntry.flow.progress as OsqueryProgress),
    filter(isNonNull),
  );

  readonly progressTable$ = this.osqueryProgress$.pipe(
    map(progress => progress.partialTable),
  );

  readonly additionalRowsAvailable$ = this.osqueryProgress$.pipe(
    map(progress => {
      const progressTableLength = BigInt(progress.partialTable?.rows?.length);
      const fullTableLength = BigInt(progress.totalRowsCount);

      if (isNonNull(progressTableLength) && isNonNull(fullTableLength)) {
        return fullTableLength - progressTableLength;
      } else {
        return null;
      }
    }),
  );

  private flagByState(targetState: FlowState): Observable<boolean> {
    return this.flowListEntry$.pipe(
      map(listEntry => listEntry.flow.state === targetState)
    );
  }

  private loadResults() {
    this.queryFlowResults({offset: 0, count: 1});
  }

  fullTableRequested() {
    this.loadResults();
  }

  trackByIndex(index: number, item: unknown): number {
    return index;
  }
}
