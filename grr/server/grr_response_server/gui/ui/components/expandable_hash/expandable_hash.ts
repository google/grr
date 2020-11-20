import { Component, Input } from '@angular/core';
import { Hash } from '../../lib/api/api_interfaces'

/** Functionality to aggregate a number of (hashType, hashValue) pairs into a single string */
export class HashTextAggregator {
  private textBuffer: string[] = [];

  private append(line: string) {
    this.textBuffer.push(line);
  }

  appendHashTypeAndValue(hashType: string, hashValue: string) {
    const line = `${hashType}: ${hashValue}`;
    this.append(line);
  }

  toString(): string {
    return this.textBuffer.join('\n');
  }
}

/**
 * Displays a default text. When the text is hovered, a pop-up appears
 * with all available hashes, together with copy-to-clipboard buttons.
 */
@Component({
  selector: 'expandable-hash',
  templateUrl: './expandable_hash.ng.html',
  styleUrls: ['./expandable_hash.scss']
})
export class ExpandableHash {
  @Input() hashes?: Hash;

  get hashesAvailable(): number {
    if (this.hashes === undefined) {
      return 0;
    }

    return [this.hashes.sha256, this.hashes.sha1, this.hashes.md5]
      .map(hash => hash ? 1 : 0 as number)
      .reduce((total, current) => total+current);
  }

  get completeHashInformation(): string {
    const hashText = new HashTextAggregator();

    if (this.hashes === undefined) {
      return '';
    }

    if (this.hashes.sha256) {
      hashText.appendHashTypeAndValue('SHA-256', this.hashes.sha256);
    }
    if (this.hashes.sha1) {
      hashText.appendHashTypeAndValue('SHA-1', this.hashes.sha1);
    }
    if (this.hashes.md5) {
      hashText.appendHashTypeAndValue('MD5', this.hashes.md5);
    }

    return hashText.toString();
  }
}
