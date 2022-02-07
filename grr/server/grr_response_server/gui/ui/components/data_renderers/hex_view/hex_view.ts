import {ChangeDetectionStrategy, Component, OnInit} from '@angular/core';
import {filter, map} from 'rxjs/operators';

import {isNonNull} from '../../../lib/preconditions';
import {ContentFetchMode, FileDetailsLocalStore} from '../../../store/file_details_local_store';

const LINE_LENGTH = 16;

const toHex = (i: number) => i.toString(16).toUpperCase();

interface Row {
  readonly hex: ReadonlyArray<string>;
  readonly chars: ReadonlyArray<string>;
}

/** Component to show hex-encoded file contents. */
@Component({
  templateUrl: './hex_view.ng.html',
  styleUrls: ['./hex_view.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HexView implements OnInit {
  readonly byteContent$ = this.fileDetailsLocalStore.blobContent$.pipe(
      filter(isNonNull),
      map(buffer => new Uint8Array(buffer)),
  );

  readonly header = [...Array.from({length: LINE_LENGTH}).keys()].map(toHex);

  readonly rows$ = this.byteContent$.pipe(
      map(arr => {
        const rows: Row[] = [];
        for (let rowI = 0; rowI < arr.length; rowI += LINE_LENGTH) {
          const bytes = [...arr.slice(rowI, rowI + LINE_LENGTH)];
          const hex = bytes.map(b => toHex(b).padStart(2, '0'));
          const chars = bytes.map(b => String.fromCharCode(b));
          rows.push({hex, chars});
        }
        return rows;
      }),
  );

  constructor(
      private readonly fileDetailsLocalStore: FileDetailsLocalStore,
  ) {}

  ngOnInit(): void {
    this.fileDetailsLocalStore.setMode(ContentFetchMode.BLOB);
    this.fileDetailsLocalStore.fetchMoreContent(
        FileDetailsLocalStore.DEFAULT_PAGE_SIZE);
  }

  rowOffset(i: number) {
    return toHex(i * LINE_LENGTH).padStart(6, '0');
  }
}
