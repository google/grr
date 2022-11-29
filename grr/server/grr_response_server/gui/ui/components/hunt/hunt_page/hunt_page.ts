import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {Observable} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {Hunt, HuntState} from '../../../lib/models/hunt';
import {isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';

/**
 * Provides the new hunt creation page.
 */
@Component({
  templateUrl: './hunt_page.ng.html',
  styleUrls: ['./hunt_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  protected readonly HuntState = HuntState;

  readonly hunt$: Observable<Hunt|null> =
      this.huntPageGlobalStore.selectedHunt$;

  constructor(
      private readonly route: ActivatedRoute,
      private readonly huntPageGlobalStore: HuntPageGlobalStore,
  ) {
    this.route.paramMap
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            map(params => params.get('id')),
            filter(isNonNull),
            )
        .subscribe(huntId => {
          this.huntPageGlobalStore.selectHunt(huntId);
        });
  }

  stopHunt() {
    this.huntPageGlobalStore.stopHunt();
  }
}
