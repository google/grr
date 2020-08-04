import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FlowFileResult, flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {BrowserProgress, CollectBrowserHistoryArgs, CollectBrowserHistoryArgsBrowser, CollectBrowserHistoryProgress, CollectBrowserHistoryResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {findFlowListEntryResultSet, FlowListEntry, FlowResultSetState, FlowState} from '@app/lib/models/flow';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {assertNonNull} from '../../../lib/preconditions';

import {Plugin} from './plugin';



declare interface BrowserRow {
  name: CollectBrowserHistoryArgsBrowser;
  friendlyName: string;
  progress: BrowserProgress;
  fetchInProgress: boolean;
  results?: FlowFileResult[];
}


/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'collect-browser-history-details',
  templateUrl: './collect_browser_history_details.ng.html',
  styleUrls: ['./collect_browser_history_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectBrowserHistoryDetails extends Plugin {
  static readonly INITIAL_COUNT = 100;
  static readonly LOAD_STEP = 100;

  readonly FINISHED = FlowState.FINISHED;

  readonly expandedRows: {[key: string]: boolean} = {};

  constructor(private readonly httpApiService: HttpApiService) {
    super();
  }

  trackByRowName(index: number, item: BrowserRow) {
    return item.name;
  }

  hasProgress$: Observable<boolean> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.progress !== undefined),
  );

  args$: Observable<CollectBrowserHistoryArgs> = this.flowListEntry$.pipe(
      map((flowListEntry) =>
              flowListEntry.flow.args as CollectBrowserHistoryArgs),
  );

  flowState$: Observable<FlowState> = this.flowListEntry$.pipe(
      map((flowListEntry) => flowListEntry.flow.state),
  );

  totalFiles$: Observable<number> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        const p = flowListEntry.flow.progress as CollectBrowserHistoryProgress;
        return (p.browsers ?? [])
            .reduce((total, cur) => total + (cur.numCollectedFiles ?? 0), 0);
      }));

  browserRows$: Observable<BrowserRow[]> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        const p = flowListEntry.flow.progress as CollectBrowserHistoryProgress;
        return (p.browsers ?? [])
            .map(bp => this.createBrowserRow(flowListEntry, bp));
      }));

  archiveUrl$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return this.httpApiService.getFlowFilesArchiveUrl(
            flowListEntry.flow.clientId, flowListEntry.flow.flowId);
      }));

  archiveFileName$: Observable<string> =
      this.flowListEntry$.pipe(map((flowListEntry) => {
        return flowListEntry.flow.clientId.replace('.', '_') + '_' +
            flowListEntry.flow.flowId + '.zip';
      }));

  loadMore(row: BrowserRow) {
    let queryNum: number;
    if (row.results) {
      queryNum = row.results.length + CollectBrowserHistoryDetails.LOAD_STEP;
    } else {
      queryNum = CollectBrowserHistoryDetails.INITIAL_COUNT;
    }
    this.queryFlowResults({
      offset: 0,
      count: queryNum,
      withTag: row.name.toUpperCase(),
    });
  }

  rowClicked(row: BrowserRow) {
    if (row.progress.numCollectedFiles === 0) {
      return;
    }

    const newValue = !this.expandedRows[row.name];
    this.expandedRows[row.name] = newValue;

    // Only load results on first expansion.
    if (newValue && row.results === undefined) {
      this.loadMore(row);
    }
  }

  private capitalize(v: string): string {
    return v[0].toUpperCase() + v.slice(1);
  }

  private createBrowserRow(fle: FlowListEntry, progress: BrowserProgress):
      BrowserRow {
    assertNonNull(progress.browser, 'progress.browser');

    const resultSet =
        findFlowListEntryResultSet(fle, undefined, progress.browser);
    const friendlyName = progress.browser.toLowerCase()
                             .split('_')
                             .map(this.capitalize)
                             .join(' ');


    return {
      name: progress.browser,
      friendlyName,
      progress,
      fetchInProgress: resultSet?.state !== FlowResultSetState.FETCHED,
      results: resultSet?.items.map((i) => {
        return flowFileResultFromStatEntry(
            (i.payload as CollectBrowserHistoryResult).statEntry!);
      }),
    };
  }
}
