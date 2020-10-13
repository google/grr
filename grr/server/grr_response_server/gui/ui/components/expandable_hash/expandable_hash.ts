import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '../../lib/api/api_interfaces'

export const MAX_CHARACTERS_IN_TRUNCATED_HASH = 9; // TODO: Check
export const SHA_256_NA_MESSAGE = 'sha256 n/a' // TODO: Check

export function truncateIfNeeded(fullText: string): string {
  const ellipsis = '...';

  if (fullText.length > MAX_CHARACTERS_IN_TRUNCATED_HASH) {
    return fullText.slice(0, MAX_CHARACTERS_IN_TRUNCATED_HASH - ellipsis.length) + ellipsis;
  } else {
    return fullText;
  }
}

@Component({
  selector: 'expandable-hash',
  templateUrl: './expandable_hash.ng.html',
  styleUrls: ['./expandable_hash.scss']
})
export class ExpandableHash implements OnInit {
  @Input() hash?: Hash;

  hovered = false;

  get truncatedHash(): string {
    // TODO: Check which hashes should be displayed if sha256 is not present
    if (this.hash && this.hash.sha256) {
      return truncateIfNeeded(this.hash.sha256);
    } else {
      return SHA_256_NA_MESSAGE; // TODO: Check uppercase
    }
  }

  constructor() { }

  ngOnInit(): void {
  }

  mouseEnter() {
    this.hovered = true;
  }
  mouseLeave() {
    this.hovered = false;
  }

}
