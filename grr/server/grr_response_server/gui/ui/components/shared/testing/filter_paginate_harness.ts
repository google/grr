import {ComponentHarness} from '@angular/cdk/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatPaginatorHarness} from '@angular/material/paginator/testing';

/** Harness for the FilterPaginate component. */
export class FilterPaginateHarness extends ComponentHarness {
  static hostSelector = 'filter-paginate';

  readonly filterInput = this.locatorFor(MatInputHarness);

  readonly paginatorTop = this.locatorFor(
    MatPaginatorHarness.with({selector: '.top-paginator'}),
  );
  readonly paginatorBottom = this.locatorFor(
    MatPaginatorHarness.with({selector: '.bottom-paginator'}),
  );
}
