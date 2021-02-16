import {ChangeDetectionStrategy, Component} from '@angular/core';
import {flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {CollectMultipleFilesArgs, CollectMultipleFilesProgress, CollectMultipleFilesResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {FlowState} from '@app/lib/models/flow';
import {combineLatest, Observable, ReplaySubject} from 'rxjs';
import {distinctUntilChanged, map, scan, startWith, takeUntil} from 'rxjs/operators';
import {translateHashToHex} from '../../../lib/api_translation/flow';


import {Plugin} from './plugin';


/**
 * Component that displays results of CollectMultipleFiles flow.
 */
@Component({
  selector: 'collect-multiple-files-details',
  templateUrl: './collect_multiple_files_details.ng.html',
  styleUrls: ['./collect_multiple_files_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectMultipleFilesDetails extends Plugin {
  readonly FINISHED = FlowState.FINISHED;

  /** Emit an integer to request `n` more result rows to be loaded. */
  private readonly resultsRequested$ = new ReplaySubject<number>(1);

  readonly hasProgress$: Observable<boolean> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.progress !== undefined),
  );

  readonly args$: Observable<CollectMultipleFilesArgs> =
      this.flowListEntry$.pipe(
          map((flowListEntry) =>
                  flowListEntry.flow.args as CollectMultipleFilesArgs),
      );

  readonly flowState$: Observable<FlowState> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.state),
  );

  readonly flowProgress$: Observable<CollectMultipleFilesProgress> =
      this.flowListEntry$.pipe(
          map((flowListEntry) =>
                  flowListEntry.flow.progress as CollectMultipleFilesProgress),
      );

  readonly totalFiles$: Observable<number> = this.flowProgress$.pipe(
      map((progress) => Number(progress?.numCollected ?? 0)));

  readonly archiveUrl$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return this.httpApiService.getFlowFilesArchiveUrl(
            flowListEntry.flow.clientId, flowListEntry.flow.flowId);
      }));

  readonly archiveFileName$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return flowListEntry.flow.clientId.replace('.', '_') + '_' +
            flowListEntry.flow.flowId + '.zip';
      }));

  readonly fileResults$ = this.flowListEntry$.pipe(map(
      flowListEntry => flowListEntry.resultSets.flatMap(
          rs => rs.items.map(item => item.payload as CollectMultipleFilesResult)
                    .map(
                        res => flowFileResultFromStatEntry(
                            res.stat!, translateHashToHex(res.hash ?? {}))))));

  constructor(private readonly httpApiService: HttpApiService) {
    super();

    // When the user clicks "Load more", trigger the loading of more flow
    // results if there are result rows that have not been loaded.
    combineLatest([
      // Total sum of files to load.
      this.resultsRequested$.pipe(
          startWith(10),
          scan((acc, cur) => acc + cur),
          ),

      // Total number of all files loaded by the UI.
      this.flowListEntry$.pipe(
          map(fle => fle.resultSets.flatMap(rs => rs.items).length),
          startWith(0),
          distinctUntilChanged(),
          ),

      // Total number of files present on the server-side.
      this.totalFiles$.pipe(
          startWith(0),
          distinctUntilChanged(),
          ),
    ])
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(([resultsRequested, resultsLoaded, totalFiles]) => {
          if (resultsRequested > resultsLoaded && resultsLoaded < totalFiles) {
            this.queryFlowResults({
              offset: 0,
              count: resultsRequested,
            });
          }
        });
  }

  loadMoreResults() {
    this.resultsRequested$.next(100);
  }
}
