import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '@app/lib/api/api_interfaces';

export class HashTextAggregator {
  private textBuffer = '';

  private append(line: string) {
    if (this.textBuffer.length > 0) {
      this.textBuffer += '\n';
    }

    this.textBuffer += line;
  }

  includeHashOfType(hashText: string, hashType: string) {
    const line = `${hashType}: ${hashText}`;
    this.append(line);
  }

  toString() {
    return this.textBuffer;
  }
}

@Component({
  selector: 'hashes',
  templateUrl: './hashes.ng.html',
  styleUrls: ['./hashes.scss']
})
export class Hashes {
  @Input() hashes?: Hash;

  get completeHashInformation(): string {
    const hashText = new HashTextAggregator();

    if (this.hashes?.sha256) {
      hashText.includeHashOfType(this.hashes.sha256, 'sha256');
    }
    if (this.hashes?.sha1) {
      hashText.includeHashOfType(this.hashes.sha1, 'sha1');
    }
    if (this.hashes?.md5) {
      hashText.includeHashOfType(this.hashes.md5, 'md5');
    }

    return hashText.toString();
  }

  get atLeastOneHashAvailable(): boolean {
    return !!this.hashes?.sha256 || !!this.hashes?.sha1 || !!this.hashes?.md5
  }

  constructor() { }
}