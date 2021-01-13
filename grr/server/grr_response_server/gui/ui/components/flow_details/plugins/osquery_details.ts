import {ChangeDetectionStrategy, Component} from '@angular/core';
import {OsqueryFlowArgs, OsqueryProgress, OsqueryResult} from '@app/lib/api/api_interfaces';
import {FlowState} from '@app/lib/models/flow';
import {isNonNull} from '@app/lib/preconditions';
import {combineLatest, concat, Observable} from 'rxjs';
import {filter, flatMap, map, startWith, takeUntil} from 'rxjs/operators';

import {Plugin} from './plugin';

/**
 * Component that displays the details (status, errors, results) for a
 * particular Osquery Flow.
 */
@Component({
  selector: 'osquery-details',
  templateUrl: './osquery_details.ng.html',
  styleUrls: ['./osquery_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryDetails extends Plugin {
  readonly flowError$ = this.flagByState(FlowState.ERROR);
  readonly flowRunning$ = this.flagByState(FlowState.RUNNING);
  readonly flowCompleted$ = this.flagByState(FlowState.FINISHED);

  private readonly osqueryResults$: Observable<OsqueryResult> =
      this.flowListEntry$.pipe(
          flatMap(listEntry => listEntry.resultSets),
          flatMap(singleResultSet => singleResultSet?.items),
          filter(isNonNull),
          map(singleItem => singleItem.payload as OsqueryResult),
      );

  private readonly osqueryProgress$: Observable<OsqueryProgress> =
      this.flowListEntry$.pipe(
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

  readonly displayTable$ = concat(
      this.progressTable$.pipe(takeUntil(this.resultsTable$)),
      this.resultsTable$,
  );

  readonly progressErrorMessage$ = this.osqueryProgress$.pipe(
      map(progress => progress.errorMessage),
      filter(isNonNull),
  );

  readonly additionalRowsAvailable$ =
      combineLatest([
        this.osqueryProgress$.pipe(
            map(progress => progress.totalRowCount),
            startWith(null),
            ),
        this.displayTable$.pipe(
            map(table => table.rows?.length),
            startWith(null),
            ),
      ])
          .pipe(
              map(([totalRowCount, displayedRowCount]) => {
                if (isNonNull(totalRowCount) && Number(totalRowCount) === 0) {
                  // Without this check the button for requesting full results
                  // will be displayed if the resulting table is empty. This is
                  // because the table property of OsqueryTable is undefined if
                  // the result contains no rows.
                  return 0;
                }

                if (isNonNull(totalRowCount) && isNonNull(displayedRowCount)) {
                  return Number(totalRowCount) - displayedRowCount;
                }

                return '?';
              }),
          );

  readonly args$: Observable<OsqueryFlowArgs> = this.flowListEntry$.pipe(
      map(flowListEntry => flowListEntry.flow.args as OsqueryFlowArgs),
  );

  readonly clientAndFlowId$ = this.flowListEntry$.pipe(
      map(fle => {
        const clientId = fle.flow.clientId;
        const flowId = fle.flow.flowId;

        if (clientId && flowId) {
          return {
            clientId,
            flowId,
          };
        } else {
          return null;
        }
      }),
      filter(isNonNull),
  );

  readonly exportCsvLink$ = this.clientAndFlowId$.pipe(
      map(ids => {
        return `/api/clients/${ids.clientId}/flows/${
            ids.flowId}/osquery-results/CSV`;
      }),
  );

  readonly collectedFilesLink$ = this.clientAndFlowId$.pipe(
      map(ids => {
        return `/api/clients/${ids.clientId}/flows/${
            ids.flowId}/results/files-archive`;
      }),
  );

  readonly numberOfRowsAvailable$ = this.displayTable$.pipe(
      map(table => table.rows?.length),
  );

  private flagByState(targetState: FlowState): Observable<boolean> {
    return this.flowListEntry$.pipe(
        map(listEntry => listEntry.flow.state === targetState));
  }

  loadCompleteResults() {
    // TODO(user): Fetch more chunks if present
    this.queryFlowResults({offset: 0, count: 1, withType: 'OsqueryResult'});
  }
}
