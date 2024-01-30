import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {filter, map, takeUntil} from 'rxjs/operators';

import {PayloadType} from '../../../../lib/models/result';
import {isNonNull} from '../../../../lib/preconditions';
import {observeOnDestroy} from '../../../../lib/reactive';
import {HuntResultDetailsGlobalStore} from '../../../../store/hunt_result_details_global_store';

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
  readonly huntId$ = this.huntResultDetailsGlobalStore.huntId$;
  readonly clientId$ = this.huntResultDetailsGlobalStore.clientId$;
  readonly timestamp$ = this.huntResultDetailsGlobalStore.timestamp$;
  readonly resultOrErrorDisplay$ =
    this.huntResultDetailsGlobalStore.resultOrErrorDisplay$;
  readonly flowWithDescriptor$ =
    this.huntResultDetailsGlobalStore.flowWithDescriptor$;
  readonly isFlowLoading$ = this.huntResultDetailsGlobalStore.isFlowLoading$;
  readonly isHuntResultLoading$ =
    this.huntResultDetailsGlobalStore.isHuntResultLoading$;

  constructor(
    private readonly activatedRoute: ActivatedRoute,
    private readonly huntResultDetailsGlobalStore: HuntResultDetailsGlobalStore,
  ) {
    this.activatedRoute.paramMap
      .pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        map((params) => ({
          key: params.get('key'),
          payloadType: (params.get('payloadType') as PayloadType) ?? undefined,
        })),
        filter((r) => isNonNull(r.key)),
      )
      .subscribe((r) => {
        this.huntResultDetailsGlobalStore.selectHuntResultId(
          r.key!,
          r.payloadType,
        );
      });
  }
}
