import {ComponentHarness} from '@angular/cdk/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

import {FilterPaginateHarness} from '../../testing/filter_paginate_harness';

/** Harness for the YaraProcessDumpResponses component. */
export class YaraProcessDumpResponsesHarness extends ComponentHarness {
  static hostSelector = 'yara-process-dump-responses';

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
    if (row >= rows.length) {
      throw new Error(`Row ${row} is out of bounds`);
    }
    const cells = await rows[row].getCells({columnName: column});
    if (cells.length !== 1) {
      throw new Error(`Cell ${column} is not defined`);
    }
    return cells[0].getText();
  }
}
