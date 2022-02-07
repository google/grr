import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {map} from 'rxjs/operators';

import {ContentFetchMode, FileDetailsLocalStore} from '../../../store/file_details_local_store';

/** Component to show plain-text file contents. */
@Component({
  templateUrl: './text_view.ng.html',
  styleUrls: ['./text_view.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TextView implements OnInit {
  readonly textContent$ = this.fileDetailsLocalStore.textContent$.pipe(
      map(textContent => textContent?.split('\n')),
  );

  readonly hasMore$ = this.fileDetailsLocalStore.hasMore$;

  constructor(
      private readonly fileDetailsLocalStore: FileDetailsLocalStore,
  ) {}

  ngOnInit(): void {
    this.fileDetailsLocalStore.setMode(ContentFetchMode.TEXT);
    this.fileDetailsLocalStore.fetchMoreContent(
        FileDetailsLocalStore.DEFAULT_PAGE_SIZE);
  }
}
