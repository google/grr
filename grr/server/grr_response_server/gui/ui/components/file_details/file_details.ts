import {Component, OnDestroy} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {combineLatest} from 'rxjs';
import {map, takeUntil} from 'rxjs/operators';

import {PathSpecPathType} from '../../lib/api/api_interfaces';
import {assertEnum, assertNonNull} from '../../lib/preconditions';
import {observeOnDestroy} from '../../lib/reactive';
import {FileDetailsLocalStore} from '../../store/file_details_local_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';

/** Component to show file contents and metadata. */
@Component({
  templateUrl: './file_details.ng.html',
  styleUrls: ['./file_details.scss'],
  providers: [FileDetailsLocalStore],
})
export class FileDetails implements OnDestroy {
  readonly DEFAULT_PAGE_LENGTH = BigInt(10000);

  readonly ngOnDestroy = observeOnDestroy();

  readonly textContent$ = this.fileDetailsLocalStore.textContent$.pipe(
      map(textContent => textContent?.split('\n')),
  );

  readonly hasMore$ = this.fileDetailsLocalStore.hasMore$;

  readonly details$ = this.fileDetailsLocalStore.details$;

  readonly fileId$ =
      combineLatest(
          [this.selectedClientGlobalStore.clientId$, this.route.paramMap])
          .pipe(
              map(([clientId, params]) => {
                assertNonNull(clientId);

                const pathType = params.get('pathType')?.toUpperCase();
                assertNonNull(pathType);
                assertEnum(pathType, PathSpecPathType);

                const path = params.get('path');
                assertNonNull(path);

                return {clientId, pathType, path};
              }),
          );

  constructor(
      private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
      private readonly fileDetailsLocalStore: FileDetailsLocalStore,
      private readonly route: ActivatedRoute,
  ) {
    this.fileId$
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe(fileId => {
          this.fileDetailsLocalStore.selectFile(fileId);
          this.fileDetailsLocalStore.fetchDetails();
          this.fileDetailsLocalStore.fetchMoreContent(this.DEFAULT_PAGE_LENGTH);
        });
  }

  loadMore() {
    this.fileDetailsLocalStore.fetchMoreContent(this.DEFAULT_PAGE_LENGTH);
  }
}
