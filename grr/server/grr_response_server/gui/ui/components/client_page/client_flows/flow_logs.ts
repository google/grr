import {LiveAnnouncer} from '@angular/cdk/a11y';
import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  ViewChild,
} from '@angular/core';
import {MatSort, MatSortModule, Sort} from '@angular/material/sort';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';

import {FlowLog} from '../../../lib/models/flow';
import {FlowStore} from '../../../store/flow_store';
import {Codeblock} from '../../shared/collection_results/data_renderer/codeblock';
import {FilterPaginate} from '../../shared/filter_paginate';
import {Timestamp} from '../../shared/timestamp';

const DISPLAYED_COLUMNS = ['timestamp', 'logMessage'];

/**
 * Component that displays flow logs.
 */
@Component({
  selector: 'flow-logs',
  templateUrl: './flow_logs.ng.html',
  imports: [
    CommonModule,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
    Timestamp,
    Codeblock,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowLogs implements AfterViewInit {
  private readonly flowStore = inject(FlowStore);
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  protected readonly displayedColumns = DISPLAYED_COLUMNS;

  readonly dataSource = new MatTableDataSource<FlowLog>();

  constructor() {
    this.flowStore.fetchFlowLogs();

    effect(() => {
      this.dataSource.data = this.flowStore.logs().slice();
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
