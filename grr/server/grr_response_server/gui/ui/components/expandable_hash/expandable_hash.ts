import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '../../lib/api/api_interfaces'

/** Max number of hash characters to be displayed when not hovered */
export const TRUNCATED_HASH_CHAR_LIMIT = 7; // TODO: Check

/** Message to display if SHA-256 is undefined */
export const SHA_256_NA_MESSAGE = 'SHA-256 n/a' // TODO: Check

/** The 'Horizontal ellipsis' character '…' */
export const ELLIPSIS = '…';

function truncate(fullText: string) {
  return fullText.slice(0, TRUNCATED_HASH_CHAR_LIMIT - ELLIPSIS.length) + ELLIPSIS;
}

/**
 * Truncates the input and appends an ellipsis if it has more characters than the limit.
 * The ellipsis is counted towards the limit as 1 character.
 */
export function truncateIfNeeded(fullText: string): string {
  if (fullText.length > TRUNCATED_HASH_CHAR_LIMIT) {
    return truncate(fullText);
  } else {
    return fullText;
  }
}

/**
 * Given multiple hashes, renders the SHA-256 value but truncated.
 * When hovered, all supplied hashes are displayed in a pop-up, together with copy-to-clipboard buttons.
 */
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
