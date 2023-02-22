import {CommonModule, KeyValue} from '@angular/common';
import {AfterViewInit, ChangeDetectionStrategy, Component, OnDestroy, TrackByFunction} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {combineLatest, Observable} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {PAYLOAD_TYPE_TRANSLATION} from '../../../lib/api_translation/result';
import {PaginatedResultView} from '../../../lib/models/flow';
import {CellComponent, ColumnDescriptor} from '../../../lib/models/result';
import {assertNonNull, isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {ExpandableHashModule} from '../../expandable_hash/module';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';
import {DrawerLinkModule} from '../../helpers/drawer_link/drawer_link_module';
import {FilterPaginate} from '../../helpers/filter_paginate/filter_paginate';
import {HumanReadableSizeModule} from '../../human_readable_size/module';
import {TimestampModule} from '../../timestamp/module';
import {UserImageModule} from '../../user_image/module';
import {FileModeModule} from '../file_mode/file_mode_module';

/**
 * A DataSource filled null elements, only to be used for the MatPaginator
 * components.
 */
class PlaceholderDataSource extends MatTableDataSource<null> {
  fillWithNullElements(totalCount: number) {
    this.data = Array.from({length: totalCount}).map(() => null);
  }
}

/** Component to show a data table with flow/hunt results. */
@Component({
  selector: 'app-data-table',
  templateUrl: './table.ng.html',
  styleUrls: ['./table.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true,
  imports: [
    CommonModule,

    MatButtonModule,
    MatIconModule,
    MatTableModule,

    FilterPaginate,
    TimestampModule,
    CopyButtonModule,
    DrawerLinkModule,
    ExpandableHashModule,
    FileModeModule,
    HumanReadableSizeModule,
    UserImageModule,
  ]
})
export class DataTableView<T> extends PaginatedResultView<T> implements
    AfterViewInit, OnDestroy {
  protected readonly CellComponent = CellComponent;

  /**
   * A DataSource filled with `totalCount` null elements, only to be used for
   * the MatPaginator components.
   */
  protected readonly paginationDataSource = new PlaceholderDataSource();

  private readonly translation$ = this.resultSource.query$.pipe(
      map(({type}) => type),
      filter(isNonNull),
      map(type => {
        const translation =
            PAYLOAD_TYPE_TRANSLATION[type as keyof typeof PAYLOAD_TYPE_TRANSLATION];
        assertNonNull(translation, `PAYLOAD_TYPE_TRANSLATION for "${type}"`);
        return translation;
      }),
  );

  protected rows$ =
      combineLatest([this.translation$, this.resultSource.results$])
          .pipe(
              map(([translation, results]) =>
                      results.map(r => translation.translateFn(r.payload))));

  protected readonly columns$: Observable<{[key: string]: ColumnDescriptor}> =
      this.translation$.pipe(map(translation => translation.columns));

  protected readonly displayedColumns$ =
      this.columns$.pipe(map(columns => Object.keys(columns)));

  readonly ngOnDestroy = observeOnDestroy(this);

  ngAfterViewInit(): void {
    this.resultSource.totalCount$.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe((totalCount) => {
          if (totalCount !== this.paginationDataSource.data.length) {
            this.paginationDataSource.fillWithNullElements(totalCount);
          }
        });

    this.paginationDataSource.paginator!.page
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe((page) => {
          this.resultSource.loadResults({
            offset: page.pageIndex * page.pageSize,
            count: page.pageSize,
          });
        });

    this.resultSource.loadResults({
      offset: this.paginationDataSource.paginator!.pageIndex *
          this.paginationDataSource.paginator!.pageSize,
      count: this.paginationDataSource.paginator!.pageSize,
    });
  }

  protected readonly trackByIndex: TrackByFunction<unknown> = (index) => index;
  protected readonly trackByKey:
      TrackByFunction<KeyValue<string, ColumnDescriptor>> = (index, pair) =>
          pair.key;
}
