import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input as routerInput,
  signal,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatDividerModule} from '@angular/material/divider';
import {MatIconModule} from '@angular/material/icon';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Title} from '@angular/platform-browser';
import {RouterModule} from '@angular/router';

import {ListHuntResultsArgs} from '../../../lib/models/hunt';
import {
  FleetCollectionStore,
  PerClientAndTypeFleetCollectionResults,
} from '../../../store/fleet_collection_store';
import {CopyButton} from '../../shared/copy_button';
import {FleetCollectionClientResults} from './fleet_collection_client_results';
import {FleetCollectionDownloadButton} from './fleet_collection_download_button';
import {FleetCollectionProgress} from './fleet_collection_progress';

const DEFAULT_FLEET_COLLECTION_RESULT_COUNT = 100;

/** Component that displays results of a single fleet collection. */
@Component({
  selector: 'fleet-collection-results',
  templateUrl: './fleet_collection_results.ng.html',
  styleUrls: ['./fleet_collection_results.scss'],
  imports: [
    CommonModule,
    CopyButton,
    FleetCollectionClientResults,
    FleetCollectionDownloadButton,
    FleetCollectionProgress,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    MatTableModule,
    MatTooltipModule,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionResults {
  protected readonly fleetCollectionStore = inject(FleetCollectionStore);

  protected readonly fleetCollectionId = routerInput<string>();

  protected readonly dataSource =
    new MatTableDataSource<PerClientAndTypeFleetCollectionResults>();
  protected readonly columns = [
    'client-icon',
    'clientId',
    'resultType',
    'resultCount',
    'details',
  ];

  protected expandedClientRows: Set<string> = new Set(); // Set of client ids

  protected isRowExpanded(row: PerClientAndTypeFleetCollectionResults) {
    return this.expandedClientRows.has(row.clientId);
  }

  protected toggleExpandedRow(row: PerClientAndTypeFleetCollectionResults) {
    if (this.isRowExpanded(row)) {
      this.expandedClientRows.delete(row.clientId);
    } else {
      this.expandedClientRows.add(row.clientId);
    }
  }

  protected readonly resultCount = signal(
    DEFAULT_FLEET_COLLECTION_RESULT_COUNT,
  );
  protected readonly resultOffset = signal(0);

  constructor() {
    inject(Title).setTitle('GRR | Fleet Collection > Results');

    this.fleetCollectionStore.pollFleetCollectionResults(
      computed<ListHuntResultsArgs | undefined>(() => {
        const fleetCollectionId = this.fleetCollectionId();
        if (!fleetCollectionId) {
          return undefined;
        }
        return {
          huntId: fleetCollectionId,
          count: this.resultCount(),
          offset: this.resultOffset(),
        };
      }),
    );

    effect(() => {
      this.dataSource.data = (
        this.fleetCollectionStore.fleetCollectionResultsPerClientAndType() ?? []
      ).slice();
    });
  }

  protected loadMore(count: number) {
    this.resultCount.set(this.resultCount() + count);
  }
}
