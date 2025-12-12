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
import {MatIconModule} from '@angular/material/icon';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

import {isRegistryValue} from '../../../../lib/api/translation/flow';
import {RegistryKey, RegistryValue} from '../../../../lib/models/flow';
import {CopyButton} from '../../copy_button';
import {FilterPaginate} from '../../filter_paginate';

type RegistryResult = RegistryKeyWithClientId | RegistryValueWithClientId;

/**
 * Registry key with client id.
 *
 * This is used to display registry keys in a table with client id column.
 */
export interface RegistryKeyWithClientId extends RegistryKey {
  clientId: string;
}

/**
 * Registry value with client id.
 *
 * This is used to display registry values in a table with client id column.
 */
export interface RegistryValueWithClientId extends RegistryValue {
  clientId: string;
}

/**
 * Component that displays a table with Windows Registry keys and values.
 */
@Component({
  selector: 'registry-results-table',
  templateUrl: './registry_results_table.ng.html',
  styleUrls: ['./registry_results_table.scss'],
  imports: [
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
    MatIconModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegistryResultsTable implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly results = input.required<readonly RegistryResult[]>();
  readonly isHuntResult = input.required<boolean>();

  readonly dataSource = new MatTableDataSource<RegistryResult>();

  protected readonly displayedColumns = computed((): string[] => {
    const availableResults = this.results();
    const columns = ['ficon'];
    if (this.isHuntResult()) {
      columns.push('clientId');
    }
    columns.push('path', 'type');
    if (availableResults.some(isRegistryValue)) {
      columns.push('value');
    }
    return columns;
  });

  constructor() {
    effect(() => {
      this.dataSource.data = this.results().slice();
    });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
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
