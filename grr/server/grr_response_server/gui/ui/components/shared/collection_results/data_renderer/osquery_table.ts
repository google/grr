import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  ViewChild,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

import {
  OsqueryRow as ApiOsqueryRow,
  OsqueryTable as ApiOsqueryTable,
} from '../../../../lib/api/api_interfaces';
import {FilterPaginate} from '../../filter_paginate';
import {Codeblock} from './codeblock';

/**
 * Component that displays an OsqueryTable object as a HTML table.
 */
@Component({
  selector: 'osquery-table',
  templateUrl: './osquery_table.ng.html',
  imports: [
    Codeblock,
    CommonModule,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OsqueryTable implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly tableData = input.required<ApiOsqueryTable>();

  dataSource = new MatTableDataSource<ApiOsqueryRow>();

  displayedColumns = computed(() => {
    return (
      this.tableData().header?.columns?.map((header) => header?.name ?? '') ??
      []
    );
  });

  constructor() {
    effect(() => {
      const rows = this.tableData()?.rows ?? [];
      if (rows.length > 0) {
        this.dataSource.data = rows.slice();
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
    this.dataSource.sortingDataAccessor = (
      row: ApiOsqueryRow,
      column: string,
    ) => {
      const value = row.values?.[this.displayedColumns().indexOf(column)];
      return value ? value : '';
    };
  }

  /** Announce the change in sort state for assistive technology. */
  protected announceSortChange(sortState: Sort) {
    if (sortState.direction) {
      this.liveAnnouncer.announce(`Sorted ${sortState.direction}`);
    } else {
      this.liveAnnouncer.announce('Sorting cleared');
    }
  }
}
