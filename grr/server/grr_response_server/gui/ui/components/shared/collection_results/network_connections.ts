import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ViewChild,
  computed,
  effect,
  inject,
  input,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

import {NetworkConnection} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
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

interface NetworkConnectionWithClientId extends NetworkConnection {
  clientId: string;
}

function networkConnectionsFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly NetworkConnectionWithClientId[] {
  return collectionResults.map((result) => {
    const networkConnection = result.payload as NetworkConnection;
    return {
      clientId: result.clientId,
      ...networkConnection,
    };
  });
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
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  readonly networkConnections = computed(() =>
    networkConnectionsFromCollectionResults(this.collectionResults()),
  );

  protected readonly dataSource =
    new MatTableDataSource<NetworkConnectionWithClientId>();

  protected readonly displayedColumns = computed(() => {
    if (this.collectionResults().some(isHuntResult)) {
      return ['clientId', ...COLUMNS];
    }
    return COLUMNS;
  });

  constructor() {
    effect(() => {
      if (this.networkConnections().length > 0) {
        this.dataSource.data = this.networkConnections().slice();
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
    // Conversion from table column name to the data accessor, this is required
    // for sorting and filtering.
    this.dataSource.sortingDataAccessor = (
      item: NetworkConnectionWithClientId,
      property: string,
    ) => {
      if (property === 'clientId') {
        return item.clientId;
      }
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
      data: NetworkConnectionWithClientId,
      filter: string,
    ) => {
      return (
        data.clientId?.toString().includes(filter) ||
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
