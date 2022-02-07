import {ChangeDetectionStrategy, Component} from '@angular/core';
import {map} from 'rxjs/operators';

import {hashName} from '../../../lib/models/flow';
import {PathSpecPathType} from '../../../lib/models/vfs';
import {FileDetailsLocalStore} from '../../../store/file_details_local_store';


/** Component to show file stat and other metadata. */
@Component({
  selector: 'app-stat-view',
  templateUrl: './stat_view.ng.html',
  styleUrls: ['./stat_view.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatView {
  readonly PathSpecPathType = PathSpecPathType;

  readonly details$ = this.fileDetailsLocalStore.details$;

  readonly pathTypeTooltip: {[key in PathSpecPathType]?: string} = {
    [PathSpecPathType.NTFS]: 'Parsed the NTFS filesystem with libfsntfs.',
    [PathSpecPathType.TSK]: 'Parsed the filesystem or image with TSK.',
  };

  readonly hashes$ = this.details$.pipe(
      map(details => details?.hash ?? {}),
      map(hash => Object.entries(hash).map(
              ([name, hash]) => ({name: hashName(name), hash}))),
      map(hashes => hashes.length ? hashes : null),
  );

  constructor(
      private readonly fileDetailsLocalStore: FileDetailsLocalStore,
  ) {}
}
