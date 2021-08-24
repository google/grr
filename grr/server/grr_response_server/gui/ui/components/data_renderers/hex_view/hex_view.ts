import {Component, OnInit} from '@angular/core';
import {filter, map} from 'rxjs/operators';

import {isNonNull} from '../../../lib/preconditions';
import {ContentFetchMode, FileDetailsLocalStore} from '../../../store/file_details_local_store';

/** Component to show hex-encoded file contents. */
@Component({
  templateUrl: './hex_view.ng.html',
  styleUrls: ['./hex_view.scss'],
})
export class HexView implements OnInit {
  readonly byteContent$ = this.fileDetailsLocalStore.blobContent$.pipe(
      filter(isNonNull),
      map(buffer => new Uint8Array(buffer)),
  );

  readonly textContent$ = this.fileDetailsLocalStore.blobContent$.pipe();

  constructor(
      private readonly fileDetailsLocalStore: FileDetailsLocalStore,
  ) {}

  ngOnInit(): void {
    this.fileDetailsLocalStore.setMode(ContentFetchMode.BLOB);
    this.fileDetailsLocalStore.fetchMoreContent(BigInt(10000));
  }
}
