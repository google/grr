import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, combineLatest, Observable} from 'rxjs';
import {filter, map, startWith, take, takeUntil} from 'rxjs/operators';

import {ColorScheme} from '../../../components/flow_details/helpers/result_accordion';
import {getHuntResultKey} from '../../../lib/api_translation/hunt';
import {getFlowTitleFromFlowName} from '../../../lib/models/flow';
import {getHuntTitle, Hunt, HuntState} from '../../../lib/models/hunt';
import {TypedHuntResultOrError} from '../../../lib/models/result';
import {isNonNull, isNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {HuntApprovalLocalStore} from '../../../store/hunt_approval_local_store';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';
import {HuntResultDetailsGlobalStore} from '../../../store/hunt_result_details_global_store';
import {UserGlobalStore} from '../../../store/user_global_store';
import {ApprovalCard, ApprovalParams} from '../../approval_card/approval_card';
import {toDurationString} from '../../form/duration_input/duration_conversion';
import {DEFAULT_EXPORT_COMMAND_PREFIX} from './hunt_results/hunt_results';

/**
 * Provides the new hunt creation page.
 */
@Component({
  standalone: false,
  templateUrl: './hunt_page.ng.html',
  styleUrls: ['./hunt_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [HuntApprovalLocalStore],
})
export class HuntPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  protected readonly colorScheme = ColorScheme;
  protected readonly HuntState = HuntState;
  protected readonly getHuntTitle = getHuntTitle;

  protected readonly defaultExportCommandPrefix = DEFAULT_EXPORT_COMMAND_PREFIX;

  readonly hunt$: Observable<Hunt | null>;

  readonly huntTotalCPU$: Observable<string>;

  @ViewChild('approvalCard', {static: false}) approvalCard?: ApprovalCard;
  private readonly approvalParams$;
  readonly latestApproval$;
  readonly requestApprovalStatus$;
  readonly hideApprovalCardContentByDefault$;
  protected readonly hasAccess$;
  protected readonly huntApprovalRoute$;
  protected readonly huntApprovalRequired$;
  protected readonly huntResultTabs$;
  readonly huntResultsByTypeCountLoading$;

  huntId = '';
  protected hideFlowArgs = true;

  protected readonly huntsOverviewRoute;

  constructor(
    private readonly activatedRoute: ActivatedRoute,
    private readonly router: Router,
    private readonly huntPageGlobalStore: HuntPageGlobalStore,
    private readonly huntApprovalLocalStore: HuntApprovalLocalStore,
    private readonly configGlobalStore: ConfigGlobalStore,
    private readonly userGlobalStore: UserGlobalStore,
    private readonly huntResultDetailsGlobalStore: HuntResultDetailsGlobalStore,
    private readonly title: Title,
  ) {
    this.exportCommandPrefix$ = this.configGlobalStore.exportCommandPrefix$;
    this.hunt$ = this.huntPageGlobalStore.selectedHunt$;
    this.huntTotalCPU$ = this.hunt$.pipe(
      map((hunt) =>
        toDurationString(hunt?.resourceUsage?.totalCPUTime ?? 0, 'long'),
      ),
    );
    this.approvalParams$ = new BehaviorSubject<ApprovalParams | null>(null);
    this.latestApproval$ = this.huntApprovalLocalStore.latestApproval$;
    this.requestApprovalStatus$ =
      this.huntApprovalLocalStore.requestApprovalStatus$;
    this.hideApprovalCardContentByDefault$ = this.latestApproval$.pipe(
      map((approval) => isNull(approval)),
      // we are only interested in the first emission, as we don't want
      // the approval card content to be hidden dynamically, only by
      // default:
      take(1),
      startWith(true),
    );
    this.hasAccess$ = this.huntApprovalLocalStore.hasAccess$;
    this.huntApprovalRoute$ = this.huntApprovalLocalStore.huntApprovalRoute$;
    this.huntApprovalRequired$ = this.userGlobalStore.currentUser$.pipe(
      map((user) => user.huntApprovalRequired),
    );
    this.huntResultTabs$ = this.huntPageGlobalStore.huntResultTabs$;
    this.huntResultsByTypeCountLoading$ =
      this.huntPageGlobalStore.huntResultsByTypeCountLoading$;
    this.huntsOverviewRoute = ['/hunts'];
    this.flowDescriptor$ = combineLatest([
      this.hunt$.pipe(
        filter(isNonNull),
        map((hunt) => hunt.flowName),
      ),
      this.configGlobalStore.flowDescriptors$,
    ]).pipe(
      map(([flowName, fds]) => {
        if (!flowName || !fds) {
          return null;
        }
        return fds.get(flowName);
      }),
      startWith(null),
    );
    this.flowTitle$ = combineLatest([this.hunt$, this.flowDescriptor$]).pipe(
      map(([hunt, desc]) => getFlowTitleFromFlowName(hunt?.flowName, desc)),
    );
    this.activatedRoute.paramMap
      .pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        map((params) => params.get('id')),
        filter(isNonNull),
      )
      .subscribe((huntId) => {
        this.huntId = huntId;
        this.huntPageGlobalStore.selectHunt(huntId);
        this.huntApprovalLocalStore.selectHunt(huntId);
      });

    combineLatest([
      this.approvalParams$,
      this.huntPageGlobalStore.selectedHuntId$,
    ])
      .pipe(
        takeUntil(this.ngOnDestroy.triggered$),
        filter(
          ([approvalParams, huntId]) =>
            isNonNull(approvalParams) && isNonNull(huntId),
        ),
      )
      .subscribe(([approvalParams, huntId]) => {
        this.huntApprovalLocalStore.requestHuntApproval({
          huntId: huntId!,
          approvers: approvalParams!.approvers,
          reason: approvalParams!.reason,
          cc: approvalParams!.cc,
        });
      });

    this.huntPageGlobalStore.selectedHunt$
      .pipe(takeUntil(this.ngOnDestroy.triggered$))
      .subscribe((hunt) => {
        if (hunt) {
          const desc = getHuntTitle(hunt);
          const info = desc ? `${desc} (${hunt.huntId})` : hunt.huntId;
          this.title.setTitle(`GRR | ${info}`);
        } else {
          this.title.setTitle('GRR');
        }
      });
  }

  protected readonly flowDescriptor$;
  protected readonly flowTitle$;

  protected readonly exportCommandPrefix$;

  requestHuntApproval(approvalParams: ApprovalParams) {
    this.approvalParams$.next(approvalParams);
  }

  openHuntResultDetailsInDrawer(
    resultOrErrorDetails: TypedHuntResultOrError,
  ): void {
    this.huntResultDetailsGlobalStore.selectHuntResultOrError(
      resultOrErrorDetails.value,
      this.huntId,
    );

    const resultKey = getHuntResultKey(resultOrErrorDetails.value, this.huntId);
    const drawerURl = `result-details/${resultKey}/${resultOrErrorDetails.payloadType}`;
    this.router.navigate([{outlets: {'drawer': drawerURl}}]);
  }

  cancelHunt() {
    this.huntPageGlobalStore.cancelHunt();
  }

  startHunt() {
    this.huntPageGlobalStore.startHunt();
  }

  copyHunt() {
    this.router.navigate(['/new-hunt'], {
      queryParams: {'huntId': this.huntId},
    });
  }

  toggleFlowArgs() {
    this.hideFlowArgs = !this.hideFlowArgs;
  }
}
