import {ClipboardModule} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {Component, computed, input, ViewEncapsulation} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatMenuModule} from '@angular/material/menu';

import {hashName, HexHash} from '../../lib/models/flow';

interface HashEntry {
  readonly name: string;
  readonly hash: string;
}

function toHashEntries(hashes: HexHash | undefined): readonly HashEntry[] {
  if (hashes === undefined) {
    return [];
  }
  return [
    {name: hashName('sha256'), hash: hashes.sha256 ?? ''},
    {name: hashName('sha1'), hash: hashes.sha1 ?? ''},
    {name: hashName('md5'), hash: hashes.md5 ?? ''},
  ].filter(({name, hash}) => !!hash);
}

/**
 * Displays a default text. When the text is hovered, a menu appears
 * with all available hashes, together with copy-to-clipboard buttons.
 */
@Component({
  selector: 'expandable-hash',
  templateUrl: './expandable_hash.ng.html',
  styleUrls: ['./expandable_hash.scss'],
  imports: [
    CommonModule,
    ClipboardModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
  ],
  // Disabled style encapsulation is needed because we want to style the
  // mat-menu. The mat-menu uses an overlay which is placed at a separate place
  // in the DOM. Thus, the only way to apply custom styles to the mat-menu is by
  // effectively making all the styles global (since ::ng-deep is deprecated).
  encapsulation: ViewEncapsulation.None,
})
export class ExpandableHash {
  readonly hashes = input.required<readonly HashEntry[], HexHash | undefined>({
    transform: toHashEntries,
  });

  protected readonly numHashes = computed(() => {
    return this.hashes().length;
  });

  protected readonly completeHashInformation = computed(() => {
    return this.hashes()
      .map(({name, hash}) => `${name}: ${hash}`)
      .join('\n');
  });

  protected readonly firstHashName = computed(() => {
    return this.hashes()[0]?.name ?? '';
  });
}
