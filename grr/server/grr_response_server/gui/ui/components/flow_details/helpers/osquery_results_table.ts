import {AfterViewInit, ChangeDetectionStrategy, Component, Input, ViewChild} from '@angular/core';
import {MatSort} from '@angular/material/sort';
import {MatTableDataSource} from '@angular/material/table';
import {BehaviorSubject} from 'rxjs';

import {OsqueryTable} from '../../../lib/api/api_interfaces';
import {isNonNull} from '../../../lib/preconditions';

interface Row {
  [column: string]: string;
}

/**
 * Component that displays an OsqueryTable object as a HTML table.
 */
@Component({
  selector: 'osquery-results-table',
  templateUrl: './osquery_results_table.ng.html',
  styleUrls: ['./osquery_results_table.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryResultsTable implements AfterViewInit {
  query?: string;
  displayedColumns: string[] = [];
  dataSource = new MatTableDataSource<Row>();

  readonly dataLength$ = new BehaviorSubject<number>(0);

  @ViewChild(MatSort) sort!: MatSort;

  @Input()
  set table(table: OsqueryTable|null) {
    if (table == null) {
      this.query = undefined;
      this.displayedColumns = [];
      this.dataSource.data = [];
      return;
    }

    this.query = table.query;

    this.displayedColumns =
        table.header?.columns?.map(header => header?.name ?? '') ?? [];

    const data: Row[] = [];
    for (const row of table.rows ?? []) {
      const r: Row = {};
      let i = 0;
      for (const value of row.values ?? []) {
        r[this.displayedColumns[i]] = value;
        i++;
      }
      data.push(r);
    }

    this.dataSource.data = data;
    this.dataLength$.next(data.length);
  }

  get atLeastOneRowPresent(): boolean {
    const rowCount = this.dataSource.data?.length;
    return isNonNull(rowCount) && rowCount > 0;
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
  }

  trackByIndex(index: number, {}): number {
    return index;
  }
}
