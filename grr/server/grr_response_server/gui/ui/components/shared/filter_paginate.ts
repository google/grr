import {CommonModule} from '@angular/common';
import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  input,
  ViewChild,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {
  FormsModule,
  ReactiveFormsModule,
  UntypedFormControl,
} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {
  MatPaginator,
  MatPaginatorModule,
  PageEvent,
} from '@angular/material/paginator';
import {MatTableDataSource} from '@angular/material/table';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100, 250, 500, 1000];
const DEFAULT_PAGE_SIZE = 10;

/**
 * Component that displays a filter and top and bottom paginators.
 */
@Component({
  selector: 'filter-paginate',
  templateUrl: './filter_paginate.ng.html',
  styleUrls: ['./filter_paginate.scss'],
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatPaginatorModule,
    ReactiveFormsModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FilterPaginate<T> implements AfterViewInit {
  @ViewChild('topPaginator') topPaginator!: MatPaginator;
  @ViewChild('bottomPaginator') bottomPaginator!: MatPaginator;

  protected readonly pageSizeOptions: readonly number[] = PAGE_SIZE_OPTIONS;
  protected pageSize = DEFAULT_PAGE_SIZE;

  readonly dataSource = input.required<MatTableDataSource<T>>();

  protected readonly searchStringControl = new UntypedFormControl('');
  private readonly searchStringSignal = toSignal(
    this.searchStringControl.valueChanges,
  );

  protected readonly dataLength = computed(() => {
    return this.dataSource()?.data?.length ?? 0;
  });

  constructor() {
    effect(() => {
      this.dataSource().filter = this.searchStringSignal();
    });
  }

  ngAfterViewInit() {
    this.dataSource().paginator = this.topPaginator;
  }

  handleBottomPageEvent(event: PageEvent) {
    // Update the top paginator
    this.topPaginator.pageIndex = event.pageIndex;
    this.topPaginator.pageSize = event.pageSize;
    // The top paginator is connected to the page source, so we need explicitly
    // trigger the change detection.
    // (See https://github.com/angular/components/issues/8417)
    // tslint:disable-next-line:angular-no-event-emitter-outside-declaring-class
    this.topPaginator.page.emit(event);
  }

  handleTopPageEvent(event: PageEvent) {
    // Update the bottom paginator
    this.bottomPaginator.pageIndex = event.pageIndex;
    this.bottomPaginator.pageSize = event.pageSize;
  }
}
