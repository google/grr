import {AfterViewInit, ChangeDetectionStrategy, Component, EventEmitter, Input, Output, ViewChild} from '@angular/core';
import {MatSort} from '@angular/material/sort';
import {MatTableDataSource} from '@angular/material/table';
import {BehaviorSubject, combineLatest, Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {RegistryKey, RegistryValue} from '../../../lib/models/flow';
import {isNonNull} from '../../../lib/preconditions';


type RegistryRow = RegistryKey|RegistryValue;

function isRegistryValue(row: RegistryRow): row is RegistryValue {
  return row.type !== 'REG_KEY';
}

function hasRegistryValue(rows: ReadonlyArray<RegistryRow>) {
  return rows.length > 0 && rows.some(isRegistryValue);
}

/**
 * Component that displays a table with Windows Registry keys and values.
 */
@Component({
  selector: 'registry-results-table',
  templateUrl: './registry_results_table.ng.html',
  styleUrls: ['./registry_results_table.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegistryResultsTable implements AfterViewInit {
  readonly results$ = new BehaviorSubject<ReadonlyArray<RegistryRow>>([]);
  readonly dataSource = new MatTableDataSource<RegistryRow>();
  @ViewChild(MatSort) sort!: MatSort;

  readonly totalCount$ = new BehaviorSubject<number|null>(null);

  readonly displayedColumns$: Observable<ReadonlyArray<string>> =
      this.results$.pipe(map(results => {
        if (hasRegistryValue(results)) {
          return ['path', 'type', 'size'];
        } else {
          return ['path', 'type'];
        }
      }));

  /**
   * Subject indicating whether a "Load more" button has to be shown.
   */
  shouldShowLoadMoreButton$: Observable<boolean> =
      combineLatest([this.results$, this.totalCount$])
          .pipe(
              map(([results, count]) =>
                      isNonNull(count) && results.length < count),
          );

  @Input()
  set results(value: ReadonlyArray<RegistryRow>|null) {
    this.results$.next(value ?? []);
    this.dataSource.data = (value ?? []) as RegistryRow[];
  }

  @Input()
  set totalCount(value: number|null) {
    this.totalCount$.next(value);
  }

  @Output() readonly loadMore = new EventEmitter<void>();

  ngAfterViewInit() {
    this.dataSource.sort = this.sort;
  }

  loadMoreClicked() {
    this.loadMore.emit();
  }

  trackByRowIndex(index: number, item: RegistryRow) {
    return index;
  }
}
