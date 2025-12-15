import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  input,
  ViewChild,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {RouterModule} from '@angular/router';

import {HuntLog} from '../../../lib/models/hunt';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {Codeblock} from '../../shared/collection_results/data_renderer/codeblock';
import {CopyButton} from '../../shared/copy_button';
import {FilterPaginate} from '../../shared/filter_paginate';
import {Timestamp} from '../../shared/timestamp';

const DISPLAYED_COLUMNS = ['timestamp', 'clientId', 'flowId', 'logMessage'];

/**
 * Component that displays fleet collection logs.
 */
@Component({
  selector: 'fleet-collection-logs',
  templateUrl: './fleet_collection_logs.ng.html',
  imports: [
    Codeblock,
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
    RouterModule,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionLogs implements AfterViewInit {
  private readonly fleetCollectionStore = inject(FleetCollectionStore);
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  protected readonly displayedColumns = DISPLAYED_COLUMNS;

  fleetCollectionId = input<string | undefined>();

  readonly dataSource = new MatTableDataSource<HuntLog>();

  constructor() {
    effect(() => {
      const fleetCollectionId = this.fleetCollectionId();
      if (fleetCollectionId) {
        this.fleetCollectionStore.fetchFleetCollectionLogs(fleetCollectionId);
      }
    });

    effect(() => {
      this.dataSource.data = this.fleetCollectionStore
        .fleetCollectionLogs()
        .slice();
    });
  }

  protected splitLines(logMessage: string): string[] {
    return logMessage.split('\\n');
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
