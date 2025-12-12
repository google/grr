import {ComponentHarness} from '@angular/cdk/testing';

import {Browser as ApiBrowser} from '../../../../lib/api/api_interfaces';
import {FileResultsTableHarness} from '../data_renderer/file_results_table/testing/file_results_table_harness';

/** Harness for the CollectBrowserHistoryResults component. */
export class CollectBrowserHistoryResultsHarness extends ComponentHarness {
  static hostSelector = 'collect-browser-history-results';

  readonly fileResultsTables = this.locatorForAll(FileResultsTableHarness);

  readonly chromiumTable = this.locatorForOptional(
    FileResultsTableHarness.with({selector: 'test'}),
  );

  async getTableForBrowser(
    browser: ApiBrowser,
  ): Promise<FileResultsTableHarness> {
    const locator = this.locatorForOptional(
      FileResultsTableHarness.with({
        className: `browser-${browser.toUpperCase()}`,
      }),
    );
    const table = await locator();
    if (!table) {
      throw new Error(`No table found for browser ${browser}`);
    }
    return table;
  }
}
