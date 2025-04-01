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
  standalone: false,
  selector: 'hunt-result-details',
  templateUrl: './hunt_result_details.ng.html',
  styleUrls: ['./hunt_result_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntResultDetails implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);
  readonly huntId$;
  readonly clientId$;
  readonly timestamp$;
  readonly resultOrErrorDisplay$;
  readonly flowWithDescriptor$;
  readonly isFlowLoading$;
  readonly isHuntResultLoading$;

  constructor(
    private readonly activatedRoute: ActivatedRoute,
    private readonly huntResultDetailsGlobalStore: HuntResultDetailsGlobalStore,
  ) {
    this.huntId$ = this.huntResultDetailsGlobalStore.huntId$;
    this.clientId$ = this.huntResultDetailsGlobalStore.clientId$;
    this.timestamp$ = this.huntResultDetailsGlobalStore.timestamp$;
    this.resultOrErrorDisplay$ =
      this.huntResultDetailsGlobalStore.resultOrErrorDisplay$;
    this.flowWithDescriptor$ =
      this.huntResultDetailsGlobalStore.flowWithDescriptor$;
    this.isFlowLoading$ = this.huntResultDetailsGlobalStore.isFlowLoading$;
    this.isHuntResultLoading$ =
      this.huntResultDetailsGlobalStore.isHuntResultLoading$;
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
