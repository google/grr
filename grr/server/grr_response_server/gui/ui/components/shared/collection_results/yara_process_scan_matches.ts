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
  YaraMatch,
  YaraProcessScanMatch,
  YaraStringMatch,
} from '../../../lib/api/api_interfaces';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {FilterPaginate} from '../filter_paginate';

const BASE_COLUMNS: readonly string[] = [
  'pid',
  'process',
  'ruleId',
  'matchOffset',
  'matchId',
  'matchData',
  'context',
];

interface YaraProcessScanMatchFlattened {
  clientId: string;
  process: Process | undefined;
  match: YaraMatch;
  context: string;
  stringMatch: YaraStringMatch;
  data: string;
}

function flattenYaraProcessScanMatches(
  collectionResults: readonly CollectionResult[],
): readonly YaraProcessScanMatchFlattened[] {
  const flattenedYaraProcessScanMatches: YaraProcessScanMatchFlattened[] = [];
  for (const result of collectionResults) {
    const yaraProcessScanMatch = result.payload as YaraProcessScanMatch;
    for (const match of yaraProcessScanMatch.match ?? []) {
      for (const stringMatch of match.stringMatches ?? []) {
        flattenedYaraProcessScanMatches.push({
          clientId: result.clientId,
          process: yaraProcessScanMatch.process,
          match,
          context: atob(stringMatch.context ?? ''),
          stringMatch,
          data: atob(stringMatch.data ?? ''),
        });
      }
    }
  }
  return flattenedYaraProcessScanMatches;
}

/**
 * Component that displays `YaraProcessScan` flow results.
 */
@Component({
  selector: 'yara-process-scan-matches',
  templateUrl: './yara_process_scan_matches.ng.html',
  styleUrls: [
    './collection_result_styles.scss',
    './yara_process_scan_matches.scss',
  ],
  imports: [
    CommonModule,
    CopyButton,
    FilterPaginate,
    MatSortModule,
    MatTableModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class YaraProcessScanMatches implements AfterViewInit {
  private readonly liveAnnouncer = inject(LiveAnnouncer);
  @ViewChild(MatSort) sort!: MatSort;

  /** Loaded results to display in the table. */
  readonly collectionResults = input.required<readonly CollectionResult[]>();

  readonly flattenedYaraProcessScanMatches = computed(() =>
    flattenYaraProcessScanMatches(this.collectionResults()),
  );

  readonly isHuntResult = computed(() =>
    this.collectionResults().some(isHuntResult),
  );

  readonly dataSource = new MatTableDataSource<YaraProcessScanMatchFlattened>();
  protected readonly displayedColumns = computed(() => {
    if (this.isHuntResult()) {
      return ['clientId', ...BASE_COLUMNS];
    }
    return BASE_COLUMNS;
  });

  constructor() {
    effect(() => {
      if (this.flattenedYaraProcessScanMatches().length > 0) {
        this.dataSource.data = this.flattenedYaraProcessScanMatches().slice();
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
      if (property === 'process') {
        return item.process?.name ?? '';
      }
      return '';
    };
    this.dataSource.filterPredicate = (
      data: YaraProcessScanMatchFlattened,
      filter: string,
    ) => {
      return (
        data.clientId?.toString().includes(filter) ||
        data.process?.pid?.toString().includes(filter) ||
        data.process?.name?.includes(filter) ||
        data.match?.ruleName?.includes(filter) ||
        data.stringMatch?.offset?.toString().includes(filter) ||
        data.stringMatch?.stringId?.includes(filter) ||
        data.data?.includes(filter) ||
        data.context?.includes(filter) ||
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
