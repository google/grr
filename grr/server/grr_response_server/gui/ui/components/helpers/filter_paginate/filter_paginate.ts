import {AfterViewInit, ChangeDetectionStrategy, Component, Input, OnDestroy, ViewChild} from '@angular/core';
import {FormsModule, ReactiveFormsModule, UntypedFormControl} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatPaginator, MatPaginatorModule, PageEvent} from '@angular/material/paginator';
import {MatTableDataSource} from '@angular/material/table';

import {observeOnDestroy} from '../../../lib/reactive';

const DEFAULT_PAGE_OPTIONS = [10, 25, 50, 100, 250, 500, 1000];

/**
 * Component that displays a filter and top and bottom paginators.
 */
@Component({
  selector: 'app-filter-paginate',
  templateUrl: './filter_paginate.ng.html',
  styleUrls: ['./filter_paginate.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,

    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
  ]
})
export class FilterPaginate<T> implements OnDestroy, AfterViewInit {
  @ViewChild('topPaginator') topPaginator!: MatPaginator;

  readonly searchStringControl = new UntypedFormControl('');

  /** dataSource used as input for mat-table. */
  private dataSourceValue: MatTableDataSource<T>|null = null;

  /** pageSizeOptions to be displayed in the paginators. */
  // Use ReadonlyArray<number> type once MatPaginator supports it:
  // https://github.com/angular/components/issues/24050
  pageSizeOptions: number[] = DEFAULT_PAGE_OPTIONS;

  private dataLengthInput: number = 0;

  readonly ngOnDestroy = observeOnDestroy(this);

  @Input()
  set dataLength(dataLength: number) {
    this.dataLengthInput = dataLength;
  }

  get dataLengthValue() {
    return this.dataLengthInput ?? (this.dataSourceValue?.data?.length ?? 0);
  }

  get hideControls() {
    return this.dataLengthValue < this.pageSizeOptions[0];
  }

  constructor() {
    this.searchStringControl.valueChanges.subscribe(searchString => {
      if (this.dataSourceValue != null) {
        this.dataSourceValue.filter = searchString;
      }
    });
  }

  @Input()
  set dataSource(dataSource: MatTableDataSource<T>|null) {
    this.dataSourceValue = dataSource;
    if (this.dataSourceValue != null) {
      this.dataSourceValue.paginator = this.topPaginator;
      this.dataSourceValue.filter = this.searchStringControl.value;
    }
  }

  ngAfterViewInit() {
    if (this.dataSourceValue != null) {
      this.dataSourceValue.paginator = this.topPaginator;
    }
  }

  // handlePageBottom handles click events and mirrors the bottom paginator
  // state in the top paginator. The bottom paginator state is synced with
  // information from the top one via the inputs in the HTML.
  handlePageBottom(event: PageEvent) {
    this.topPaginator.pageSize = event.pageSize;
    this.topPaginator.pageIndex = event.pageIndex;
    this.topPaginator.page.emit(event);
  }
}
