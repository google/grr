import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '@app/lib/api/api_interfaces';

export class HashText {
  private currentBuffer = '';

  private append(line: string) {
    if (this.currentBuffer.length > 0) {
      this.currentBuffer += '\n';
    }

    this.currentBuffer += line;
  }

  includeHashOfType(hashText: string, hashType: string) {
    const line = `${hashType}: ${hashText}`;
    this.append(line);
  }

  toString() {
    return this.currentBuffer;
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
    const hashText = new HashText();

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
