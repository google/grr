import {AfterViewInit, Component, ElementRef, EventEmitter, Input, OnChanges, Output, ViewChild} from '@angular/core';

/**
 * A container loading more contents through infinite scroll.
 */
@Component({
  selector: 'app-infinite-list',
  templateUrl: './infinite_list.ng.html',
  styleUrls: ['./infinite_list.scss'],
})
export class InfiniteList implements AfterViewInit, OnChanges {
  @Input() isLoading: boolean|null = null;
  @Input() hasMore: boolean|null = null;

  @Output() readonly loadMore = new EventEmitter<void>();

  @ViewChild('footer') footer!: ElementRef<HTMLElement>;

  private isBottomVisible = false;

  private readonly observer = new IntersectionObserver((entries) => {
    if (entries.length > 0) {
      this.isBottomVisible = entries[0].isIntersecting;
      this.ngOnChanges();
    }
  });

  ngAfterViewInit() {
    this.observer.observe(this.footer.nativeElement);
  }

  ngOnChanges() {
    // Load more when the footer scrolls into view or when isLoading/hasMore
    // changes while the footer is already in view.
    if (!this.isLoading && this.hasMore && this.isBottomVisible) {
      this.loadMore.emit();
    }
  }
}
