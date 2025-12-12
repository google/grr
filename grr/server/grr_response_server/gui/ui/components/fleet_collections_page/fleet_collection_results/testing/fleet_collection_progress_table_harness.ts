import {ComponentHarness} from '@angular/cdk/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

/** Harness for the FleetCollectionProgressTable component. */
export class FleetCollectionProgressTableHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-progress-table';

  readonly table = this.locatorFor(MatTableHarness);

  async getRows(): Promise<MatRowHarness[]> {
    const table = await this.table();
    return table.getRows();
  }

  async getCellText(row: number, column: string): Promise<string> {
    const rows = await this.getRows();
    if (row >= rows.length) {
      throw new Error(`Row ${row} is out of bounds`);
    }
    const cells = await rows[row].getCells({columnName: column});
    if (cells.length === 0) {
      throw new Error(`No cell found for column ${column}`);
    }
    return cells[0].getText();
  }
}
