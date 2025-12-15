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

import {
  Process,
  YaraProcessDumpInformation,
  YaraProcessDumpResponse,
} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {FilterPaginate} from '../filter_paginate';

const BASE_COLUMNS: readonly string[] = [
  'pid',
  'cmdline',
  'memoryRegionsCount',
  'error',
];

declare interface FlattenedYaraProcessDumpResponse {
  clientId: string;
  process?: Process;
  error?: string;
  memoryRegionsCount: number;
}

function flattenedYaraProcessDumpResponsesFromCollectionResults(
  collectionResults: readonly CollectionResult[],
): readonly FlattenedYaraProcessDumpResponse[] {
  const flattenedYaraProcessDumpResponses: FlattenedYaraProcessDumpResponse[] =
    [];
  for (const result of collectionResults) {
    const yaraProcessDumpResponse = result.payload as YaraProcessDumpResponse;
    for (const process of yaraProcessDumpResponse.dumpedProcesses ?? []) {
      flattenedYaraProcessDumpResponses.push({
        clientId: result.clientId,
        process: process.process,
        error: process.error,
        memoryRegionsCount:
          (process as YaraProcessDumpInformation).memoryRegions?.length ?? 0,
      });
    }
    for (const error of yaraProcessDumpResponse.errors ?? []) {
      flattenedYaraProcessDumpResponses.push({
        clientId: result.clientId,
        process: error.process,
        error: error.error ?? '',
        memoryRegionsCount: 0,
      });
    }
  }
  return flattenedYaraProcessDumpResponses;
}

/** Component that displays `YaraProcessDumpResponse` flow results. */
@Component({
  selector: 'yara-process-dump-responses',
  templateUrl: './yara_process_dump_responses.ng.html',
  styleUrls: ['./collection_result_styles.scss'],
  imports: [
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class YaraProcessDumpResponses implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  readonly flattenedYaraProcessDumpResponses = computed(() =>
    flattenedYaraProcessDumpResponsesFromCollectionResults(
      this.collectionResults(),
    ),
  );

  readonly isHuntResult = computed(() =>
    this.collectionResults().some(isHuntResult),
  );

  readonly dataSource =
    new MatTableDataSource<FlattenedYaraProcessDumpResponse>();
  protected readonly displayedColumns = computed(() => {
    if (this.isHuntResult()) {
      return ['clientId', ...BASE_COLUMNS];
    }
    return BASE_COLUMNS;
  });

  constructor() {
    effect(() => {
      if (this.flattenedYaraProcessDumpResponses().length > 0) {
        this.dataSource.data = this.flattenedYaraProcessDumpResponses().slice();
      }
    });
  }

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
    // Conversion from table column name to the data accessor, this is required
    // for sorting and filtering.
    this.dataSource.sortingDataAccessor = (item, property) => {
      if (property === 'clientId') {
        return item.clientId;
      }
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
        data.clientId?.toString().includes(filter) ||
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
