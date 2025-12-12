import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input as routerInput,
  signal,
  ViewChild,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {Title} from '@angular/platform-browser';

import {HuntError} from '../../../lib/models/hunt';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {Codeblock} from '../../shared/collection_results/data_renderer/codeblock';
import {CopyButton} from '../../shared/copy_button';
import {FilterPaginate} from '../../shared/filter_paginate';
import {Timestamp} from '../../shared/timestamp';

const DEFAULT_FLEET_COLLECTION_ERROR_COUNT = 100;

const COLUMNS = ['clientId', 'timestamp', 'logMessage', 'backtrace'];

/** Component that displays errors of a single fleet collection. */
@Component({
  selector: 'fleet-collection-errors',
  templateUrl: './fleet_collection_errors.ng.html',
  styleUrls: ['./fleet_collection_errors.scss'],
  imports: [
    Codeblock,
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatTableModule,
    MatSortModule,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionErrors {
  protected readonly fleetCollectionStore = inject(FleetCollectionStore);
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  protected readonly fleetCollectionId = routerInput<string>();

  readonly dataSource = new MatTableDataSource<HuntError>();
  readonly columns = COLUMNS;

  protected readonly errorCount = signal(DEFAULT_FLEET_COLLECTION_ERROR_COUNT);
  protected readonly errorOffset = signal(0);

  constructor() {
    inject(Title).setTitle('GRR | Fleet Collection > Errors');

    effect(() => {
      this.dataSource.data = this.fleetCollectionStore
        .fleetCollectionErrors()
        .slice();
    });

    this.fleetCollectionStore.getFleetCollectionErrors(
      computed(() => {
        const fleetCollectionId = this.fleetCollectionId();
        if (!fleetCollectionId) {
          return undefined;
        }
        return {
          huntId: fleetCollectionId,
          count: this.errorCount(),
          offset: this.errorOffset(),
        };
      }),
    );
  }

  protected loadMore(count: number) {
    this.errorCount.set(this.errorCount() + count);
  }

  protected splitLines(text: string) {
    if (!text) {
      return [];
    }
    return text.split('\n');
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
