import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ViewChild,
  effect,
  inject,
  input,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

import {NetworkConnection} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {NetworkConnectionFamilyPipe} from '../../../pipes/network_connection/network_connection_family_pipe';
import {NetworkConnectionTypePipe} from '../../../pipes/network_connection/network_connection_type_pipe';
import {CopyButton} from '../copy_button';
import {FilterPaginate} from '../filter_paginate';

const COLUMNS: readonly string[] = [
  'pid',
  'processName',
  'state',
  'type',
  'family',
  'localIP',
  'localPort',
  'remoteIP',
  'remotePort',
];

function networkConnectionsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly NetworkConnection[] {
  return collectionResults.map((result) => result.payload as NetworkConnection);
}

/**
 * Component that displays NetworkConnections collection results.
 */
@Component({
  selector: 'network-connections',
  templateUrl: './network_connections.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
    NetworkConnectionFamilyPipe,
    NetworkConnectionTypePipe,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NetworkConnections implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<
    readonly NetworkConnection[],
    readonly CollectionResult[]
  >({
    transform: networkConnectionsFromCollectionResults,
  });

  protected readonly dataSource = new MatTableDataSource<NetworkConnection>();
  protected readonly displayedColumns = COLUMNS;

  constructor() {
    effect(() => {
      if (this.collectionResults().length > 0) {
        this.dataSource.data = this.collectionResults().slice();
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
    // Conversion from table column name to the data accessor, this is required
    // for sorting and filtering.
    this.dataSource.sortingDataAccessor = (
      item: NetworkConnection,
      property: string,
    ) => {
      if (property === 'pid') {
        return item.pid ?? '';
      }
      if (property === 'processName') {
        return item.processName ?? '';
      }
      if (property === 'state') {
        return item.state ?? '';
      }
      if (property === 'type') {
        return item.type ?? '';
      }
      if (property === 'family') {
        return item.family ?? '';
      }
      if (property === 'localIP') {
        return item.localAddress?.ip ?? '';
      }
      if (property === 'localPort') {
        return item.localAddress?.port ?? '';
      }
      if (property === 'remoteIP') {
        return item.remoteAddress?.ip ?? '';
      }
      if (property === 'remotePort') {
        return item.remoteAddress?.port ?? '';
      }
      return '';
    };
    this.dataSource.filterPredicate = (
      data: NetworkConnection,
      filter: string,
    ) => {
      return (
        data.pid?.toString().includes(filter) ||
        data.processName?.includes(filter) ||
        data.state?.toString().includes(filter) ||
        data.type?.toString().includes(filter) ||
        data.family?.toString().includes(filter) ||
        data.localAddress?.ip?.includes(filter) ||
        data.localAddress?.port?.toString().includes(filter) ||
        data.remoteAddress?.ip?.includes(filter) ||
        data.remoteAddress?.port?.toString().includes(filter) ||
        false
      );
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
