import {ChangeDetectionStrategy, Component, Input, OnDestroy} from '@angular/core';
import {Router} from '@angular/router';
import {map} from 'rxjs/operators';

import {getFileBlobUrl} from '../../lib/api/http_api_service';
import {FileIdentifier} from '../../lib/models/vfs';
import {isNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {FileDetailsLocalStore} from '../../store/file_details_local_store';

/** Component to show file contents and metadata. */
@Component({
  'selector': 'app-file-details',
  templateUrl: './file_details.ng.html',
  styleUrls: ['./file_details.scss'],
  providers: [FileDetailsLocalStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileDetails implements OnDestroy {
  readonly DEFAULT_PAGE_LENGTH = BigInt(10000);

  readonly ngOnDestroy = observeOnDestroy(this);

  readonly hasMore$ = this.fileDetailsLocalStore.hasMore$;

  readonly details$ = this.fileDetailsLocalStore.details$;

  readonly fileId$ = this.fileDetailsLocalStore.file$;

  readonly downloadUrl$ = this.fileDetailsLocalStore.file$.pipe(
      map((f) => f ? getFileBlobUrl(f.clientId, f.pathType, f.path) : null));

  readonly hasContents$ = this.fileDetailsLocalStore.details$.pipe(
      map(details => !!details?.lastContentCollected?.timestamp));

  @Input()
  set file(file: FileIdentifier|null|undefined) {
    this.fileDetailsLocalStore.selectFile(file ?? undefined);

    if (isNonNull(file)) {
      this.fileDetailsLocalStore.fetchDetails();
      this.fileDetailsLocalStore.fetchMoreContent(this.DEFAULT_PAGE_LENGTH);
    }
  }

  readonly isRecollecting$ = this.fileDetailsLocalStore.isRecollecting$;

  constructor(
      private readonly fileDetailsLocalStore: FileDetailsLocalStore,
      readonly router: Router,
  ) {}

  loadMore() {
    this.fileDetailsLocalStore.fetchMoreContent(this.DEFAULT_PAGE_LENGTH);
  }

  recollect() {
    this.fileDetailsLocalStore.recollectFile();
  }
}
