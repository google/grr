import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '../../lib/api/api_interfaces'

export const MAX_CHARACTERS_IN_TRUNCATED_HASH = 9; // TODO: Check
export const SHA_256_NA_MESSAGE = 'sha256 n/a' // TODO: Check

function truncate(fullText: string) {
  const ellipsis = '...';
  return fullText.slice(0, MAX_CHARACTERS_IN_TRUNCATED_HASH - ellipsis.length) + ellipsis;
}

export function truncateIfNeeded(fullText: string): string {
  if (fullText.length > MAX_CHARACTERS_IN_TRUNCATED_HASH) {
    return truncate(fullText);
  } else {
    return fullText;
  }
}

@Component({
  selector: 'expandable-hash',
  templateUrl: './expandable_hash.ng.html',
  styleUrls: ['./expandable_hash.scss']
})
export class ExpandableHash {
  @Input() hashes?: Hash;

  shouldDisplayPopup = false;

  get truncatedSha256(): string {
    if (this.hashes?.sha256) {
      return truncateIfNeeded(this.hashes.sha256);
    } else {
      return SHA_256_NA_MESSAGE;
    }
  }

  constructor() { }

  mouseEnteredTruncatedHash() {
    this.shouldDisplayPopup = true;
  }
  mouseLeftPopup() {
    this.shouldDisplayPopup = false;
  }
}
