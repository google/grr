import {CommonModule} from '@angular/common';
import {AfterViewInit, ChangeDetectionStrategy, Component, Input, OnDestroy, ViewChild} from '@angular/core';
import {FormsModule, ReactiveFormsModule, UntypedFormControl} from '@angular/forms';
import {MatIconModule} from '@angular/material/icon';
import {MatLegacyFormFieldModule} from '@angular/material/legacy-form-field';
import {MatLegacyInputModule} from '@angular/material/legacy-input';
import {LegacyPageEvent, MatLegacyPaginator, MatLegacyPaginatorModule} from '@angular/material/legacy-paginator';
import {MatLegacyTableDataSource} from '@angular/material/legacy-table';

import {assertNonNull, isNonNull} from '../../../lib/preconditions';
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
    CommonModule,
    FormsModule,
    ReactiveFormsModule,

    MatLegacyFormFieldModule,
    MatIconModule,
    MatLegacyInputModule,
    MatLegacyPaginatorModule,
  ]
})
export class FilterPaginate<T> implements OnDestroy, AfterViewInit {
  @ViewChild('topPaginator') topPaginator!: MatLegacyPaginator;

  readonly searchStringControl = new UntypedFormControl('');

  /** dataSource used as input for mat-table. */
  private dataSourceValue: MatLegacyTableDataSource<T>|null = null;

  /** pageSizeOptions to be displayed in the paginators. */
  // Use readonly number [] type once MatLegacyPaginatorModule supports it:
  // https://github.com/angular/components/issues/24050
  pageSizeOptions: number[] = DEFAULT_PAGE_OPTIONS;

  private dataLengthInput = 0;
  private dataLengthSet = false;

  readonly ngOnDestroy = observeOnDestroy(this);

  @Input() showFilterInput = true;

  @Input()
  set dataLength(dataLength: number) {
    this.dataLengthSet = true;
    this.dataLengthInput = dataLength;
  }

  get dataLengthValue() {
    return this.dataLengthSet ? this.dataLengthInput ?? 0 :
                                (this.dataSourceValue?.data?.length ?? 0);
  }

  get hideControls() {
    return this.dataLengthValue < this.pageSizeOptions[0];
  }

  constructor() {
    this.searchStringControl.valueChanges.subscribe(searchString => {
      if (isNonNull(this.dataSourceValue)) {
        this.dataSourceValue.filter = searchString;
      }
    });
  }

  @Input()
  set dataSource(dataSource: MatLegacyTableDataSource<T>|null) {
    this.dataSourceValue = dataSource;
    if (isNonNull(this.dataSourceValue)) {
      this.dataSourceValue.paginator = this.topPaginator;
      this.dataSourceValue.filter = this.searchStringControl.value;
    }
  }

  ngAfterViewInit() {
    assertNonNull(this.topPaginator, 'topPaginator');
    if (isNonNull(this.dataSourceValue)) {
      this.dataSourceValue.paginator = this.topPaginator;
    }
  }

  // handlePageBottom handles click events and mirrors the bottom paginator
  // state in the top paginator. The bottom paginator state is synced with
  // information from the top one via the inputs in the HTML.
  handlePageBottom(event: LegacyPageEvent) {
    this.topPaginator.pageSize = event.pageSize;
    this.topPaginator.pageIndex = event.pageIndex;
    this.topPaginator.page.emit(event);
  }
}
