import {ComponentHarness} from '@angular/cdk/testing';
import {MatSortHarness} from '@angular/material/sort/testing';
import {
  MatCellHarness,
  MatRowHarness,
  MatTableHarness,
} from '@angular/material/table/testing';

import {RecentClientApprovalHarness} from '../../shared/approvals/testing/recent_client_approval_harness';

/** Harness for the ClientSearch component. */
export class ClientSearchHarness extends ComponentHarness {
  static hostSelector = 'client-search';

  readonly table = this.locatorFor(MatTableHarness);
  readonly tableSort = this.locatorFor(MatSortHarness);

  readonly recentApprovals = this.locatorForAll(RecentClientApprovalHarness);

  async getRows(): Promise<MatRowHarness[]> {
    const table = await this.table();
    if (!table) {
      throw new Error('Table not found');
    }
    return table.getRows();
  }

  async getCell(row: number, column: string): Promise<MatCellHarness> {
    const rows = await this.getRows();
    if (row >= rows.length) {
      throw new Error(`Row ${row} is out of bounds`);
    }
    const cells = await rows[row].getCells({columnName: column});
    if (cells.length === 0) {
      throw new Error(`No cell found for column ${column}`);
    }
    return cells[0];
  }

  async getCellText(row: number, column: string): Promise<string> {
    return (await this.getCell(row, column)).getText();
  }

  async getTableSort(): Promise<MatSortHarness> {
    const sort = await this.tableSort();
    if (!sort) {
      throw new Error('Table sort not found');
    }
    return sort;
  }
}
