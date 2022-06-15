import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {Observable} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {ApiHunt} from '../../../lib/api/api_interfaces';
import {isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntPageLocalStore} from '../../../store/hunt_page_local_store';

/**
 * Provides the new hunt creation page.
 */
@Component({
  templateUrl: './hunt_page.ng.html',
  styleUrls: ['./hunt_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [HuntPageLocalStore],
})
export class HuntPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  readonly hunt$: Observable<ApiHunt|null> =
      this.huntPageLocalStore.selectedHunt$;

  constructor(
      private readonly route: ActivatedRoute,
      private readonly huntPageLocalStore: HuntPageLocalStore,
  ) {
    this.route.paramMap
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            map(params => params.get('id')),
            filter(isNonNull),
            )
        .subscribe(huntId => {
          this.huntPageLocalStore.selectHunt(huntId);
        });
  }
}
