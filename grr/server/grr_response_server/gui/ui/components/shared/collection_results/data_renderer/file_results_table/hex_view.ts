import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {FileContent} from '../../../../../lib/models/vfs';

const LINE_LENGTH = 16;

interface Row {
  readonly hex: readonly string[];
  readonly chars: readonly string[];
}

function toHex(i: number) {
  return i.toString(16).toUpperCase();
}

function toRows(blobContent: FileContent | undefined): Row[] {
  if (!blobContent) {
    return [];
  }
  const arr = new Uint8Array(blobContent?.blobContent ?? new ArrayBuffer(0));
  const rows: Row[] = [];
  for (let rowI = 0; rowI < arr.length; rowI += LINE_LENGTH) {
    const bytes = [...arr.slice(rowI, rowI + LINE_LENGTH)];
    const hex = bytes.map((b) => toHex(b).padStart(2, '0'));
    const chars = bytes.map((b) => String.fromCharCode(b));
    rows.push({hex, chars});
  }
  return rows;
}

/** Component to show hex-encoded file contents. */
@Component({
  selector: 'hex-view',
  templateUrl: './hex_view.ng.html',
  styleUrls: ['./hex_view.scss'],
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HexView {
  readonly blobContent = input.required<Row[], FileContent | undefined>({
    transform: toRows,
  });

  readonly header = [...Array.from({length: LINE_LENGTH}).keys()].map(toHex);

  rowOffset(i: number) {
    return toHex(i * LINE_LENGTH).padStart(6, '0');
  }
}
