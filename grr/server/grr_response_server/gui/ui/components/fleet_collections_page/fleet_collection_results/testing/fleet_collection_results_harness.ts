import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

import {FleetCollectionClientResultsHarness} from './fleet_collection_client_results_harness';
import {FleetCollectionDownloadButtonHarness} from './fleet_collection_download_button_harness';
import {FleetCollectionProgressHarness} from './fleet_collection_progress_harness';

/** Harness for the FleetCollectionResults component. */
export class FleetCollectionResultsHarness extends ComponentHarness {
  static hostSelector = 'fleet-collection-results';

  readonly progress = this.locatorForOptional(FleetCollectionProgressHarness);
  private readonly overviewContainer = this.locatorFor('.overview-container');
  private readonly loadMoreButton = this.locatorForOptional(
    MatButtonHarness.with({text: 'Load 100 more'}),
  );
  readonly downloadButton = this.locatorForOptional(
    FleetCollectionDownloadButtonHarness,
  );

  readonly resultsTable = this.locatorFor(MatTableHarness);
  private readonly detailWrapper = this.locatorForAll('.detail-wrapper');
  readonly fleetCollectionClientResults = this.locatorForAll(
    FleetCollectionClientResultsHarness,
  );

  async loadedResultsText(): Promise<string> {
    const overviewContainer = await this.overviewContainer();
    return overviewContainer.text();
  }

  async hasLoadMoreButton(): Promise<boolean> {
    const loadMoreButton = await this.loadMoreButton();
    return loadMoreButton !== null;
  }

  async getRows(): Promise<MatRowHarness[]> {
    const table = await this.resultsTable();
    const rows = await table.getRows();
    const filteredRows: MatRowHarness[] = [];
    for (const row of rows) {
      // We are filtering for rows with a computer icon as expandable rows
      // are otherwise counted as separate rows in the table.
      if ((await row.getCells({columnName: 'client-icon'})).length > 0) {
        filteredRows.push(row);
      }
    }
    return filteredRows;
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

  async getToggleDetailsButton(row: number): Promise<MatButtonHarness> {
    const rows = await this.getRows();
    if (row >= rows.length) {
      throw new Error(`Row ${row} is out of bounds`);
    }
    const cells = await rows[row].getCells({columnName: 'details'});
    if (cells.length === 0) {
      throw new Error('No details column found');
    }
    const button = await cells[0].getHarness(MatButtonHarness);
    return button;
  }

  async toggleDetails(row: number): Promise<void> {
    const button = await this.getToggleDetailsButton(row);
    await button.click();
  }

  async isDetailsExpanded(row: number): Promise<boolean> {
    const detailWrapper = await this.detailWrapper();
    if (row >= detailWrapper.length) {
      throw new Error(`Row ${row} is out of bounds`);
    }
    return detailWrapper[row].hasClass('detail-wrapper-expanded') ?? false;
  }
}
