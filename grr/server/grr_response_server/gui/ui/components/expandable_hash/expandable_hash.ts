import {Component, Input, ViewEncapsulation} from '@angular/core';

import {hashName, HexHash} from '../../lib/models/flow';

interface HashEntry {
  readonly name: string;
  readonly hash: string;
}

/**
 * Displays a default text. When the text is hovered, a menu appears
 * with all available hashes, together with copy-to-clipboard buttons.
 */
@Component({
  selector: 'expandable-hash',
  templateUrl: './expandable_hash.ng.html',
  styleUrls: ['./expandable_hash.scss'],

  // Disabled style encapsulation is needed because we want to style the
  // mat-menu. The mat-menu uses an overlay which is placed at a separate place
  // in the DOM. Thus, the only way to apply custom styles to the mat-menu is by
  // effectively making all the styles global (since ::ng-deep is deprecated).
  encapsulation: ViewEncapsulation.None,
})
export class ExpandableHash {
  @Input() hashes?: HexHash;

  get hashesAvailable(): number {
    return this.hashesWithNames.length;
  }

  get hashesWithNames(): ReadonlyArray<HashEntry> {
    // Return hashes in order of most usage:
    return [
      {name: hashName('sha256'), hash: this.hashes?.sha256 ?? ''},
      {name: hashName('sha1'), hash: this.hashes?.sha1 ?? ''},
      {name: hashName('md5'), hash: this.hashes?.md5 ?? ''},
    ].filter(({name, hash}) => !!hash);
  }

  get completeHashInformation(): string {
    return this.hashesWithNames.map(({name, hash}) => `${name}: ${hash}`)
        .join('\n');
  }

  get firstHashName() {
    return this.hashesWithNames[0]?.name ?? '';
  }

  trackByName(index: number, entry: HashEntry) {
    return entry.name;
  }
}
