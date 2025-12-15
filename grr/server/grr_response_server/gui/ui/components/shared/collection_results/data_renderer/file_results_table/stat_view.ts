import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import {MatTooltipModule} from '@angular/material/tooltip';

import {HexHash, hashName} from '../../../../../lib/models/flow';
import {
  FileOrDirectory,
  PathSpecPathType,
  isFile,
} from '../../../../../lib/models/vfs';
import {HumanReadableByteSizePipe} from '../../../../../pipes/human_readable/human_readable_byte_size_pipe';
import {CopyButton} from '../../../copy_button';
import {Timestamp} from '../../../timestamp';

interface HashEntry {
  readonly name: string;
  readonly hash: HexHash;
}

/** Component to show file stat and other metadata. */
@Component({
  selector: 'stat-view',
  templateUrl: './stat_view.ng.html',
  styleUrls: ['./stat_view.scss'],
  imports: [
    CommonModule,
    CopyButton,
    HumanReadableByteSizePipe,
    MatTooltipModule,
    Timestamp,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatView {
  readonly PathSpecPathType = PathSpecPathType;

  readonly path = input.required<FileOrDirectory | undefined>();

  hashes = computed<readonly HashEntry[] | undefined>(() => {
    const path = this.path();
    if (path && isFile(path)) {
      const hash = path?.hash ?? {};
      return Object.entries(hash).map(([name, hash]) => ({
        name: hashName(name),
        hash,
      }));
    }
    return undefined;
  });

  protected readonly isFile = isFile;
}
