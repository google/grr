import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {filter, map, takeUntil} from 'rxjs/operators';

import {createOptionalDate} from '../../../../lib/api_translation/primitive';
import {toResultKey} from '../../../../lib/models/result';
import {isNonNull} from '../../../../lib/preconditions';
import {observeOnDestroy} from '../../../../lib/reactive';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';

/**
 * Component displaying the details for a single hunt result.
 */
@Component({
  selector: 'hunt-result-details',
  templateUrl: './hunt_result_details.ng.html',
  styleUrls: ['./hunt_result_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntResultDetails implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  constructor(
      private readonly activatedRoute: ActivatedRoute,
      private readonly huntPageGlobalStore: HuntPageGlobalStore) {
    this.activatedRoute.paramMap
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            map(params => params.get('key')),
            filter(isNonNull),
            )
        .subscribe(key => {
          this.huntPageGlobalStore.selectResult(key);
        });
  }

  readonly isLoading$ =
      this.huntPageGlobalStore.huntResults$.pipe(map(state => state.isLoading));

  readonly huntId$ = this.huntPageGlobalStore.selectedHuntResultId$.pipe(
      map(r => toResultKey(r).flowId ?? 'Unknown'));
  readonly clientId$ = this.huntPageGlobalStore.selectedHuntResultId$.pipe(
      map(r => toResultKey(r).clientId ?? 'Unknown'));
  readonly timestamp$ = this.huntPageGlobalStore.selectedHuntResultId$.pipe(
      map(r => createOptionalDate(toResultKey(r).timestamp ?? '')));

  readonly payload$ = this.huntPageGlobalStore.selectedHuntResult$.pipe(
      map(r => JSON.stringify(r?.payload, null, 2)));
}
