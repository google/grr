import {ComponentHarness} from '@angular/cdk/testing';
import {MatSortHarness} from '@angular/material/sort/testing';
import {MatRowHarness, MatTableHarness} from '@angular/material/table/testing';

import {FilterPaginateHarness} from '../../../testing/filter_paginate_harness';
import {CodeblockHarness} from './codeblock_harness';

/** Harness for the OsqueryTable component. */
export class OsqueryTableHarness extends ComponentHarness {
  static hostSelector = 'osquery-table';

  readonly queryCodeblock = this.locatorFor(CodeblockHarness);
  readonly filterPaginate = this.locatorFor(FilterPaginateHarness);
  readonly table = this.locatorFor(MatTableHarness);
  readonly tableSort = this.locatorFor(MatSortHarness);

  async getRows(): Promise<MatRowHarness[]> {
    const table = await this.table();
    return table.getRows();
  }
}
