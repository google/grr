import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {
  Browser as ApiBrowser,
  CollectBrowserHistoryResult as ApiCollectBrowserHistoryResult,
} from '../../../lib/api/api_interfaces';
import {translateStatEntry} from '../../../lib/api/translation/flow';
import {CollectionResult} from '../../../lib/models/result';
import {
  FileResultsTable,
  FlowFileResult,
} from './data_renderer/file_results_table/file_results_table';

function flowFileResultsPerBrowserFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): Map<ApiBrowser, FlowFileResult[]> {
  const result = new Map<ApiBrowser, FlowFileResult[]>();

  for (const flowResult of collectionResults) {
    const browser = (flowResult.payload as ApiCollectBrowserHistoryResult)
      .browser;
    const apiStatEntry = (flowResult.payload as ApiCollectBrowserHistoryResult)
      .statEntry;
    if (browser && apiStatEntry) {
      if (!result.has(browser)) {
        result.set(browser, []);
      }
      const statEntry = translateStatEntry(apiStatEntry);
      result.get(browser)!.push({
        statEntry,
        clientId: flowResult.clientId,
      });
    }
  }
  return result;
}

/** Component that displays `CollectBrowserHistory` flow results. */
@Component({
  selector: 'collect-browser-history-results',
  templateUrl: './collect_browser_history_results.ng.html',
  imports: [CommonModule, FileResultsTable],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectBrowserHistoryResults {
  collectionResults = input.required<
    Map<ApiBrowser, FlowFileResult[]>,
    readonly CollectionResult[]
  >({
    transform: flowFileResultsPerBrowserFromCollectionResults,
  });
}
