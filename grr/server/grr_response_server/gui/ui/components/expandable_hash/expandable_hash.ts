import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '../../lib/api/api_interfaces'

@Component({
  selector: 'expandable-hash',
  templateUrl: './expandable_hash.ng.html',
  styleUrls: ['./expandable_hash.scss']
})
export class ExpandableHash implements OnInit {
  readonly MAX_CHARACTERS_IN_TRUNCATED_HASH = 9; // TODO: Check
  readonly SHA_256_NA_MESSAGE = 'sha256 n/a'

  @Input() hash?: Hash;

  static truncateIfNeeded(fullText: string, maxCharacters: number): string {
    const ellipsis = '...';

    if (fullText.length > maxCharacters && maxCharacters > ellipsis.length) {
      return fullText.slice(0, maxCharacters - ellipsis.length) + ellipsis;
    } else {
      return fullText;
    }
  }

  get truncatedHash(): string {
    // TODO: Check which hashes should be displayed if sha256 is not present
    if (this.hash && this.hash.sha256) {
      return ExpandableHash.truncateIfNeeded(this.hash.sha256, this.MAX_CHARACTERS_IN_TRUNCATED_HASH);
    } else {
      return this.SHA_256_NA_MESSAGE; // TODO: Check uppercase
    }
  }

  constructor() { }

  ngOnInit(): void {
  }

}
