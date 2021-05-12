import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';

/** Component that displays an expendable flow result row. */
@Component({
  selector: 'result-accordion',
  templateUrl: './result_accordion.ng.html',
  styleUrls: ['./result_accordion.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultAccordion {
  @Input() title?: string;

  @Input() hasMoreResults: boolean = true;

  isOpen: boolean = false;

  @Output() readonly loadMore = new EventEmitter<void>();

  private firstOpen = true;

  get hasResults() {
    return this.hasMoreResults || !this.firstOpen;
  }

  toggle() {
    if (this.firstOpen) {
      this.firstOpen = false;
      this.loadMore.emit();
    }

    this.isOpen = !this.isOpen;
  }

  loadMoreClicked() {
    this.loadMore.emit();
  }
}
