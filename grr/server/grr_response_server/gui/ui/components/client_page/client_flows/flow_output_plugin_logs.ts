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

import {OutputPluginLogEntry} from '../../../lib/models/flow';
import {FlowStore} from '../../../store/flow_store';
import {Codeblock} from '../../shared/collection_results/data_renderer/codeblock';
import {FilterPaginate} from '../../shared/filter_paginate';
import {Timestamp} from '../../shared/timestamp';

const DISPLAYED_COLUMNS = [
  'timestamp',
  'outputPluginId',
  'logEntryType',
  'message',
];

/**
 * Component that displays flow output plugin logs.
 */
@Component({
  selector: 'flow-output-plugin-logs',
  templateUrl: './flow_output_plugin_logs.ng.html',
  imports: [
    Codeblock,
    CommonModule,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowOutputPluginLogs implements AfterViewInit {
  private readonly flowStore = inject(FlowStore);
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  protected readonly displayedColumns = DISPLAYED_COLUMNS;

  readonly dataSource = new MatTableDataSource<OutputPluginLogEntry>();

  constructor() {
    this.flowStore.fetchAllFlowOutputPluginLogs();

    effect(() => {
      this.dataSource.data = this.flowStore.outputPluginLogs().slice();
    });
  }

  protected splitLines(message: string): string[] {
    return message?.split('\\n');
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
