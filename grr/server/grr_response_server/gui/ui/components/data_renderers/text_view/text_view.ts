import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {map} from 'rxjs/operators';

import {
  ContentFetchMode,
  FileDetailsLocalStore,
} from '../../../store/file_details_local_store';

/** Component to show plain-text file contents. */
@Component({
  standalone: false,
  templateUrl: './text_view.ng.html',
  styleUrls: ['./text_view.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TextView implements OnInit {
  readonly textContent$;

  readonly hasMore$;

  constructor(private readonly fileDetailsLocalStore: FileDetailsLocalStore) {
    this.textContent$ = this.fileDetailsLocalStore.textContent$.pipe(
      map((textContent) => textContent?.split('\n')),
    );
    this.hasMore$ = this.fileDetailsLocalStore.hasMore$;
  }

  ngOnInit(): void {
    this.fileDetailsLocalStore.setMode(ContentFetchMode.TEXT);
    this.fileDetailsLocalStore.fetchMoreContent(
      FileDetailsLocalStore.DEFAULT_PAGE_SIZE,
    );
  }
}
