import {ChangeDetectionStrategy, Component} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {combineLatest} from 'rxjs';
import {map} from 'rxjs/operators';

import {PathSpecPathType} from '../../lib/api/api_interfaces';
import {assertEnum, isNonNull} from '../../lib/preconditions';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';

/** Component to show file contents and metadata. */
@Component({
  template: '<app-file-details [file]="file$ | async"></app-file-details>',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FileDetailsPage {
  readonly file$ = combineLatest([
                     this.selectedClientGlobalStore.clientId$,
                     this.route.paramMap,
                   ])
                       .pipe(
                           map(([clientId, params]) => {
                             const pathType =
                                 params.get('pathType')?.toUpperCase();
                             const path = params.get('path');

                             if (isNonNull(clientId) && isNonNull(pathType) &&
                                 isNonNull(path)) {
                               assertEnum(pathType, PathSpecPathType);
                               return {clientId, pathType, path};
                             } else {
                               return null;
                             }
                           }),
                       );

  constructor(
      private readonly selectedClientGlobalStore: SelectedClientGlobalStore,
      private readonly route: ActivatedRoute,
  ) {}
}
