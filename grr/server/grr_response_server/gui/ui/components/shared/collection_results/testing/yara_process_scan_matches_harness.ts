import {ComponentHarness} from '@angular/cdk/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

import {FilterPaginateHarness} from '../../testing/filter_paginate_harness';

/** Harness for the YaraProcessScanMatches component. */
export class YaraProcessScanMatchesHarness extends ComponentHarness {
  static hostSelector = 'yara-process-scan-matches';

  readonly paginator = this.locatorForOptional(FilterPaginateHarness);
  readonly table = this.locatorForOptional(MatTableHarness);

  async getRows(): Promise<MatRowHarness[]> {
    const table = await this.table();
    if (!table) {
      throw new Error('Table is not defined');
    }
    return table.getRows() ?? [];
  }

  async getCellText(row: number, column: string): Promise<string> {
    const table = await this.table();
    if (!table) {
      throw new Error('Table is not defined');
    }
    const rows = await table.getRows();
    const cells = await rows[row].getCells({columnName: column});
    return cells[0].getText();
  }
}
