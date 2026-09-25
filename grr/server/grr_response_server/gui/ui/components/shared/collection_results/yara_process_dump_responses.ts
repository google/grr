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

import {
  Process,
  YaraProcessDumpInformation,
  YaraProcessDumpResponse,
} from '../../../lib/api/api_interfaces';
import {CollectionResult} from '../../../lib/models/result';
import {FilterPaginate} from '../filter_paginate';

const BASE_COLUMNS: readonly string[] = [
  'pid',
  'cmdline',
  'memoryRegionsCount',
  'error',
];

declare interface FlattenedYaraProcessDumpResponse {
  process?: Process;
  error?: string;
  memoryRegionsCount: number;
}

function flattenedYaraProcessDumpResponsesFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly FlattenedYaraProcessDumpResponse[] {
  return (
    collectionResults
      .map((res) => res.payload as YaraProcessDumpResponse)
      .flatMap((res) => [...(res.dumpedProcesses ?? []), ...(res.errors ?? [])])
      .map((res) => ({
        process: res.process,
        memoryRegionsCount:
          (res as YaraProcessDumpInformation).memoryRegions?.length ?? 0,
        error: res.error,
      })) ?? []
  );
}

/** Component that displays `YaraProcessDumpResponse` flow results. */
@Component({
  selector: 'yara-process-dump-responses',
  templateUrl: './yara_process_dump_responses.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [CommonModule, FilterPaginate, MatSortModule, MatTableModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class YaraProcessDumpResponses implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<
    readonly FlattenedYaraProcessDumpResponse[],
    readonly CollectionResult[]
  >({
    transform: flattenedYaraProcessDumpResponsesFromCollectionResults,
  });

  readonly dataSource =
    new MatTableDataSource<FlattenedYaraProcessDumpResponse>();
  protected readonly displayedColumns = BASE_COLUMNS;

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
    this.dataSource.sortingDataAccessor = (item, property) => {
      if (property === 'pid') {
        return item.process?.pid ?? '';
      }
      if (property === 'cmdline') {
        return item.process?.cmdline?.join(' ') ?? '';
      }
      if (property === 'memoryRegionsCount') {
        return item.memoryRegionsCount;
      }
      if (property === 'error') {
        return item.error ?? '';
      }
      return '';
    };
    this.dataSource.filterPredicate = (
      data: FlattenedYaraProcessDumpResponse,
      filter: string,
    ) => {
      return (
        data.process?.pid?.toString().includes(filter) ||
        data.process?.cmdline?.join(' ').includes(filter) ||
        data.error?.includes(filter) ||
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
