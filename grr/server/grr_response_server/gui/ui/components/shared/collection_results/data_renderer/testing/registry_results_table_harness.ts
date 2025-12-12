import {ComponentHarness} from '@angular/cdk/testing';
import {MatSortHarness} from '@angular/material/sort/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

/** Harness for the RegistryResultsTable component. */
export class RegistryResultsTableHarness extends ComponentHarness {
  static hostSelector = 'registry-results-table';

  readonly table = this.locatorFor(MatTableHarness);
  readonly tableSort = this.locatorFor(MatSortHarness);

  async getRows(): Promise<MatRowHarness[]> {
    const table = await this.table();
    return table.getRows();
  }

  async getCellText(row: number, column: string): Promise<string> {
    const table = await this.table();
    const rows = await table.getRows();
    const cells = await rows[row].getCells({columnName: column});
    if (cells.length === 0) {
      throw new Error(`No cell found for column ${column}`);
    }
    return cells[0].getText();
  }
}
