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

import {OsqueryHeader as ApiOsqueryHeader} from '../../../../lib/api/api_interfaces';
import {CopyButton} from '../../copy_button';
import {FilterPaginate} from '../../filter_paginate';
import {Codeblock} from './codeblock';

/** OsqueryRow proto mapping. */
export declare interface OsqueryRow {
  readonly clientId: string;
  readonly values?: readonly string[];
}

/** OsqueryTableData proto mapping. */
export declare interface OsqueryTableData {
  readonly query?: string;
  readonly header?: ApiOsqueryHeader;
  readonly rows?: readonly OsqueryRow[];
}

/**
 * Component that displays an OsqueryTable object as a HTML table.
 */
@Component({
  selector: 'osquery-table',
  templateUrl: './osquery_table.ng.html',
  imports: [
    Codeblock,
    CommonModule,
    CopyButton,
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
  readonly tableData = input.required<OsqueryTableData>();
  readonly isHuntResult = input.required<boolean>();

  protected readonly dataSource = new MatTableDataSource<OsqueryRow>();

  protected readonly valueColumns = computed(() => {
    return (
      this.tableData().header?.columns?.map((header) => header?.name ?? '') ??
      []
    );
  });

  protected readonly displayedColumns = computed(() => {
    if (this.isHuntResult()) {
      return ['clientId', ...this.valueColumns()];
    }
    return this.valueColumns();
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
    this.dataSource.sortingDataAccessor = (row: OsqueryRow, column: string) => {
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
