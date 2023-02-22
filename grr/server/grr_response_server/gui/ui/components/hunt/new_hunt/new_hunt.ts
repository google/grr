import {AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, ViewChild} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, combineLatest, Observable, of} from 'rxjs';
import {filter, map, startWith, switchMap, takeUntil, tap} from 'rxjs/operators';

import {FlowWithDescriptor} from '../../../lib/models/flow';
import {Hunt} from '../../../lib/models/hunt';
import {isNonNull, isNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntApprovalGlobalStore} from '../../../store/hunt_approval_global_store';
import {NewHuntLocalStore} from '../../../store/new_hunt_local_store';
import {UserGlobalStore} from '../../../store/user_global_store';
import {ApprovalCard, ApprovalParams} from '../../approval_card/approval_card';
import {TitleEditor} from '../../form/title_editor/title_editor';

import {ClientsForm} from './clients_form/clients_form';
import {OutputPluginsForm} from './output_plugins_form/output_plugins_form';
import {ParamsForm} from './params_form/params_form';

/**
 * Provides the new hunt creation page.
 */
@Component({
  templateUrl: './new_hunt.ng.html',
  styleUrls: ['./new_hunt.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [NewHuntLocalStore],
})
export class NewHunt implements AfterViewInit {
  @ViewChild('clientsForm', {static: false}) clientsForm!: ClientsForm;
  @ViewChild('paramsForm', {static: false}) paramsForm!: ParamsForm;
  @ViewChild('outputPluginsForm', {static: false})
  outputPluginsForm!: OutputPluginsForm;
  @ViewChild('approvalCard', {static: false}) approvalCard?: ApprovalCard;
  @ViewChild('titleEditor', {static: false}) titleEditor?: TitleEditor;

  readonly flowWithDescriptor$: Observable<FlowWithDescriptor|null> =
      this.newHuntLocalStore.flowWithDescriptor$;
  readonly originalHunt$: Observable<Hunt|null> =
      this.newHuntLocalStore.originalHunt$;
  readonly huntId$ = this.newHuntLocalStore.huntId$;
  readonly huntApprovalRequired$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.huntApprovalRequired));
  protected readonly latestApproval$ =
      this.huntApprovalGlobalStore.latestApproval$;
  protected readonly huntApprovalRoute$ =
      this.huntApprovalGlobalStore.huntApprovalRoute$;
  private readonly approvalParams$ =
      new BehaviorSubject<ApprovalParams|null>(null);
  private readonly requestApprovalStatus$ =
      this.huntApprovalGlobalStore.requestApprovalStatus$;

  readonly ngOnDestroy = observeOnDestroy(this);

  huntName = '';
  protected readonly huntsOverviewRoute = [
    '', {
      outlets: {
        'primary': [
          'hunts',
        ]
      }
    }
  ];

  readonly hasOrigin$ =
      combineLatest([this.flowWithDescriptor$, this.originalHunt$])
          .pipe(
              map(([flowDesc, hunt]) => {
                if (!flowDesc && !hunt) {
                  return false;
                }
                return true;
              }),
              startWith(false),
          );

  readonly canCreateHunt$ = this.hasOrigin$;

  ngAfterViewInit() {
    if (this.titleEditor) {
      this.titleEditor.startEdit();
      this.changeDetectorRef.detectChanges();
    }
  }

  constructor(
      private readonly route: ActivatedRoute,
      private readonly newHuntLocalStore: NewHuntLocalStore,
      private readonly huntApprovalGlobalStore: HuntApprovalGlobalStore,
      private readonly router: Router,
      private readonly userGlobalStore: UserGlobalStore,
      private readonly changeDetectorRef: ChangeDetectorRef,
  ) {
    this.route.queryParams.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(params => {
          const clientId = params['clientId'];
          const flowId = params['flowId'];
          const huntId = params['huntId'];

          if (clientId && flowId) {
            this.newHuntLocalStore.selectOriginalFlow(clientId, flowId);
            return;
          }

          if (huntId) {
            this.newHuntLocalStore.selectOriginalHunt(huntId);
            return;
          }

          throw new Error(
              'Must provide either a base Hunt or Test Flow, but nothing was provided.');
        });

    combineLatest([this.approvalParams$, this.huntId$])
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(
                ([approvalParams, huntId]) =>
                    isNonNull(approvalParams) && isNonNull(huntId)))
        .subscribe(
            ([approvalParams, huntId]) => {
              this.huntApprovalGlobalStore.requestHuntApproval({
                huntId: huntId!,
                approvers: approvalParams!.approvers,
                reason: approvalParams!.reason,
                cc: approvalParams!.cc,
              });
            },
        );
    combineLatest([this.huntApprovalRequired$, this.huntId$])
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(([isRequired,
                     huntId]) => isNonNull(isRequired) && isNonNull(huntId)),
            switchMap(([isRequired, huntId]) => {
              return isRequired ?
                  this.requestApprovalStatus$.pipe(
                      filter(isNonNull),
                      // tslint:disable-next-line:enforce-name-casing
                      map((_) => {
                        return huntId;
                      }),
                      ) :
                  of(huntId);
            }))
        .subscribe((huntId) => {
          this.router.navigate([`/hunts/${huntId}`]);
        });

    this.newHuntLocalStore.originalHunt$
        .pipe(
            tap(v => {
              if (isNull(v)) {
                return;
              }
              if (v.description) {
                this.huntName = v.description;
              }
              if (v.clientRuleSet) {
                this.clientsForm.setFormState(v.clientRuleSet);
              }
              if (v.safetyLimits) {
                this.paramsForm.setFormState(v.safetyLimits);
              }
              if (v.outputPlugins) {
                this.outputPluginsForm.setFormState(v.outputPlugins);
              }
            }),
            )
        .subscribe();
  }

  updateTitle(title: string) {
    this.huntName = title;
  }

  runHunt() {
    const safetyLimits = this.paramsForm.buildSafetyLimits();
    const rules = this.clientsForm.buildRules();
    const outputPlugins = this.outputPluginsForm.buildOutputPlugins();
    this.newHuntLocalStore.runHunt(
        this.huntName, safetyLimits, rules, outputPlugins);
    // approval's submitRequest() method will trigger an emits of parameters
    // needed for request approval to new_hunt component. This is handled in
    // requestHuntApproval() method in new_hunt.
    if (this.approvalCard) {
      this.approvalCard.submitRequest();
    }
  }

  requestHuntApproval(approvalParams: ApprovalParams) {
    this.approvalParams$.next(approvalParams);
  }
}
