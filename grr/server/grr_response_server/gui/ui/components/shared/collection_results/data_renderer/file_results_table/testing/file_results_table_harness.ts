import {
  BaseHarnessFilters,
  ComponentHarness,
  HarnessPredicate,
} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatIconHarness} from '@angular/material/icon/testing';
import {MatSortHarness} from '@angular/material/sort/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

import {FileContentHarness} from './file_content_harness';

interface FileResultsTableHarnessFilters extends BaseHarnessFilters {
  /** Only find instances whose class name matches the given value. */
  className?: string;
}

/** Harness for the FileResultsTable component. */
export class FileResultsTableHarness extends ComponentHarness {
  static hostSelector = 'file-results-table';

  readonly table = this.locatorFor(MatTableHarness);
  readonly tableSort = this.locatorFor(MatSortHarness);

  private readonly detailWrapper = this.locatorForAll('.detail-wrapper');
  private readonly fileContent = this.locatorForOptional(FileContentHarness);

  static with(
    options: FileResultsTableHarnessFilters = {},
  ): HarnessPredicate<FileResultsTableHarness> {
    return new HarnessPredicate(FileResultsTableHarness, options).addOption(
      'className',
      options.className,
      async (harness, className) => {
        const host = await harness.host();
        return await host.hasClass(className);
      },
    );
  }

  async getSelector(): Promise<string> {
    return (await (await this.host()).getAttribute('class')) ?? '';
  }

  async getRows(): Promise<MatRowHarness[]> {
    const table = await this.table();
    const rows = await table.getRows();
    const filteredRows: MatRowHarness[] = [];
    for (const row of rows) {
      // We are filtering for rows with a file icon as expandable rows
      // are otherwise counted as separate rows in the table.
      if ((await row.getCells({columnName: 'ficon'})).length > 0) {
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

  async getStatusIconName(row: number): Promise<string | null> {
    const rows = await this.getRows();
    const cells = await rows[row].getCells({columnName: 'status'});
    if (cells.length === 0) {
      throw new Error('No status column found');
    }
    const icon = await cells[0].getHarness(MatIconHarness);
    return icon.getName();
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

  async hasFileContent(): Promise<boolean> {
    return !!(await this.fileContent());
  }
}
