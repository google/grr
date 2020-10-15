import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '@app/lib/api/api_interfaces';

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

/** Component that renders hashes of various types with copy-to-clipboard functionality */
@Component({
  selector: 'hashes',
  templateUrl: './hashes.ng.html',
  styleUrls: ['./hashes.scss']
})
export class Hashes {
  @Input() hashes?: Hash;

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

  get atLeastOneHashAvailable(): boolean {
    if (this.hashes === undefined) {
      return false;
    }

    return (this.hashes.sha256 ?? this.hashes.sha1 ?? this.hashes.md5) !== undefined;
  }

  constructor() { }
}
