import {ChangeDetectionStrategy, Component, ViewChild} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import {BehaviorSubject, combineLatest, Observable, of} from 'rxjs';
import {filter, map, switchMap, takeUntil} from 'rxjs/operators';

import {ApiHuntApproval} from '../../../lib/api/api_interfaces';
import {FlowWithDescriptor} from '../../../lib/models/flow';
import {isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {NewHuntLocalStore} from '../../../store/new_hunt_local_store';
import {UserGlobalStore} from '../../../store/user_global_store';
import {Approval, ApprovalParams} from '../../approval/approval';

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
export class NewHunt {
  @ViewChild('clientsForm', {static: false}) clientsForm!: ClientsForm;
  @ViewChild('paramsForm', {static: false}) paramsForm!: ParamsForm;
  @ViewChild('outputPluginsForm', {static: false})
  outputPluginsForm!: OutputPluginsForm;
  @ViewChild('approval', {static: false}) approval?: Approval;
  readonly flowWithDescriptor$: Observable<FlowWithDescriptor|undefined> =
      this.newHuntLocalStore.flowWithDescriptor$;
  readonly huntId$ = this.newHuntLocalStore.huntId$;
  readonly huntApprovalRequired$ = this.userGlobalStore.currentUser$.pipe(
      map(user => user.huntApprovalRequired));
  private readonly approvalParams$ =
      new BehaviorSubject<ApprovalParams|null>(null);
  private readonly huntRequestStatus$ =
      this.newHuntLocalStore.huntRequestStatus$;
  readonly ngOnDestroy = observeOnDestroy(this);
  huntName = '';

  constructor(
      private readonly route: ActivatedRoute,
      private readonly newHuntLocalStore: NewHuntLocalStore,
      private readonly router: Router,
      private readonly userGlobalStore: UserGlobalStore,
  ) {
    this.route.queryParams.pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(params => {
          const clientId = params['clientId'];
          const flowId = params['flowId'];
          this.newHuntLocalStore.selectOriginalFlow(clientId, flowId);
        });
    combineLatest([this.approvalParams$, this.huntId$])
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(
                ([approvalParams, huntId]) =>
                    isNonNull(approvalParams) && isNonNull(huntId)))
        .subscribe(
            ([approvalParams, huntId]) => {
              const request: ApiHuntApproval = {
                reason: approvalParams!.reason,
                notifiedUsers: approvalParams!.approvers,
                emailCcAddresses: approvalParams!.cc,
              };
              this.newHuntLocalStore.requestHuntApproval(huntId!, request);
            },
        );
    combineLatest([this.huntApprovalRequired$, this.huntId$])
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            filter(([isRequired,
                     huntId]) => isNonNull(isRequired) && isNonNull(huntId)),
            switchMap(([isRequired, huntId]) => {
              return isRequired ?
                  this.huntRequestStatus$.pipe(
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
    if (this.approval) {
      this.approval.submitRequest();
    }
  }

  requestHuntApproval(approvalParams: ApprovalParams) {
    this.approvalParams$.next(approvalParams);
  }
}
