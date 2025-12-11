import {ComponentHarness} from '@angular/cdk/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

/** Harness for the SoftwarePackagez component. */
export class SoftwarePackagezHarness extends ComponentHarness {
  static hostSelector = 'software-packagez';

  readonly table = this.locatorForOptional(MatTableHarness);

  async getRows(index: number): Promise<MatRowHarness[]> {
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

  async getNumCells(row: number): Promise<number> {
    const table = await this.table();
    if (!table) {
      throw new Error('Table is not defined');
    }
    const rows = await table.getRows();
    if (row >= rows.length) {
      throw new Error(`Row ${row} is out of bounds`);
    }
    const cells = await rows[row].getCells();
    return cells.length;
  }
}
