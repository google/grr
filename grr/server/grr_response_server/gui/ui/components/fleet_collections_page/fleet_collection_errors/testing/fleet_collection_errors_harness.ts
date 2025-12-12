import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatTableHarness} from '@angular/material/table/testing';

/** Harness for the FleetCollectionErrors component. */
export class FleetCollectionErrorsHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-errors';

  private readonly loadedErrorsContainer = this.locatorFor(
    '.loaded-errors-container',
  );
  private readonly loadMoreButton = this.locatorForOptional(
    MatButtonHarness.with({text: 'Load 100 more'}),
  );
  readonly table = this.locatorFor(MatTableHarness);

  async getCellText(row: number, column: string): Promise<string> {
    const table = await this.table();
    const rows = await table.getRows();
    const rowCells = await rows[row].getCells({columnName: column});
    return rowCells[0].getText();
  }

  async loadedErrorsText(): Promise<string> {
    const loadedErrorsContainer = await this.loadedErrorsContainer();
    return loadedErrorsContainer.text();
  }

  async hasLoadMoreButton(): Promise<boolean> {
    const loadMoreButton = await this.loadMoreButton();
    return loadMoreButton !== null;
  }
}
