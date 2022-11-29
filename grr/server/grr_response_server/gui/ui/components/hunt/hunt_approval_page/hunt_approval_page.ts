import {ChangeDetectionStrategy, Component, OnDestroy} from '@angular/core';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute} from '@angular/router';
import {combineLatest, Observable} from 'rxjs';
import {filter, map, startWith, takeUntil} from 'rxjs/operators';

import {ForemanClientRuleSetMatchMode, ForemanClientRuleType, ForemanIntegerClientRuleForemanIntegerField, ForemanIntegerClientRuleOperator, ForemanLabelClientRuleMatchMode, ForemanRegexClientRuleForemanStringField} from '../../../lib/api/api_interfaces';
import {RequestStatusType} from '../../../lib/api/track_request';
import {assertNonNull, isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {HuntApprovalPageGlobalStore} from '../../../store/hunt_approval_page_global_store';
import {UserGlobalStore} from '../../../store/user_global_store';
import {FlowArgsViewData} from '../../flow_args_view/flow_args_view';
import {ColorScheme} from '../../flow_details/helpers/result_accordion';
import {toDurationString} from '../../form/duration_input/duration_conversion';

/** Component that displays a hunt request. */
@Component({
  templateUrl: './hunt_approval_page.ng.html',
  styleUrls: ['./hunt_approval_page.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntApprovalPage implements OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  protected readonly approval$ = this.huntApprovalPageGlobalStore.approval$;

  private readonly canGrant$ =
      combineLatest([this.approval$, this.userGlobalStore.currentUser$])
          .pipe(
              map(([approval, user]) => approval &&
                      user.name !== approval.requestor &&
                      !approval.approvers.includes(user.name)));

  protected readonly requestInProgress$ =
      this.huntApprovalPageGlobalStore.grantRequestStatus$.pipe(
          map(status => status?.status === RequestStatusType.SENT));

  protected readonly disabled$ =
      combineLatest([this.canGrant$, this.requestInProgress$, this.approval$])
          .pipe(
              map(([canGrant, requestInProgress, approval]) => !canGrant ||
                      requestInProgress || approval?.status.type === 'valid'),
          );

  constructor(
      readonly route: ActivatedRoute,
      private readonly huntApprovalPageGlobalStore: HuntApprovalPageGlobalStore,
      private readonly title: Title,
      private readonly userGlobalStore: UserGlobalStore,
      private readonly configGlobalStore: ConfigGlobalStore

  ) {
    route.paramMap
        .pipe(
            takeUntil(this.ngOnDestroy.triggered$),
            )
        .subscribe((params) => {
          const huntId = params.get('huntId');
          const requestor = params.get('requestor');
          const approvalId = params.get('approvalId');

          assertNonNull(huntId, 'huntId');
          assertNonNull(requestor, 'requestor');
          assertNonNull(approvalId, 'approvalId');

          this.huntApprovalPageGlobalStore.selectHuntApproval(
              {huntId, requestor, approvalId});
        });

    this.huntApprovalPageGlobalStore.approval$
        .pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(approval => {
          if (!approval) {
            this.title.setTitle('GRR | Approval');
          } else {
            const hunt = approval.subject;
            this.title.setTitle(
                `GRR | Approval for ${approval.requestor} on ${hunt.huntId}`);
          }
        });
  }

  protected readonly flowDescriptor$ =
      combineLatest([
        this.approval$.pipe(
            filter(isNonNull), map(approval => approval.subject.flowName)),
        this.configGlobalStore.flowDescriptors$
      ])
          .pipe(
              map(([flowName, fds]) => {
                if (!flowName || !fds) {
                  return null;
                }
                return fds.get(flowName);
              }),
              startWith(null));

  protected readonly flowArgsViewData$: Observable<FlowArgsViewData|null> =
      combineLatest([
        this.approval$.pipe(
            filter(isNonNull), map(approval => approval.subject.flowArgs)),
        this.flowDescriptor$
      ])
          .pipe<FlowArgsViewData|null, FlowArgsViewData|null>(
              map(([args, fd]) => {
                if (!args || !fd) {
                  return null;
                }
                return {
                  flowDescriptor: fd,
                  flowArgs: args,
                };
              }),
              startWith(null as FlowArgsViewData|null),
          );

  protected convertToUnitTime(seconds: BigInt) {
    return toDurationString(Number(seconds), 'long');
  }

  protected grantApproval() {
    this.huntApprovalPageGlobalStore.grantApproval();
  }

  protected readonly RegexClientRuleForemanStringField =
      ForemanRegexClientRuleForemanStringField;
  protected readonly ClientRuleSetMatchMode = ForemanClientRuleSetMatchMode;
  protected readonly LabelClientRuleMatchMode = ForemanLabelClientRuleMatchMode;
  protected readonly IntegerClientRuleOperator =
      ForemanIntegerClientRuleOperator;
  protected readonly ClientRuleType = ForemanClientRuleType;

  protected readonly BigInt = BigInt;
  protected readonly ColorScheme = ColorScheme;

  protected readonly regexConditionsNames = new Map<
      ForemanRegexClientRuleForemanStringField|undefined, string>([
    [ForemanRegexClientRuleForemanStringField.UNSET, 'Unset'],
    [ForemanRegexClientRuleForemanStringField.USERNAMES, 'Usernames'],
    [ForemanRegexClientRuleForemanStringField.UNAME, 'Uname'],
    [ForemanRegexClientRuleForemanStringField.FQDN, 'FQDN'],
    [ForemanRegexClientRuleForemanStringField.HOST_IPS, 'Host IPs'],
    [ForemanRegexClientRuleForemanStringField.CLIENT_NAME, 'Client Name'],
    [
      ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION,
      'Client Description'
    ],
    [ForemanRegexClientRuleForemanStringField.SYSTEM, 'System'],
    [ForemanRegexClientRuleForemanStringField.MAC_ADDRESSES, 'MAC Addresses'],
    [ForemanRegexClientRuleForemanStringField.KERNEL_VERSION, 'Kernel Version'],
    [ForemanRegexClientRuleForemanStringField.OS_VERSION, 'OS Version'],
    [ForemanRegexClientRuleForemanStringField.OS_RELEASE, 'OS Release'],
    [ForemanRegexClientRuleForemanStringField.CLIENT_LABELS, 'Client Labels'],
    [undefined, 'Undefined Condition Field'],
  ]);

  protected readonly integerConditionsNames = new Map<
      ForemanIntegerClientRuleForemanIntegerField|undefined, string>([
    [ForemanIntegerClientRuleForemanIntegerField.INSTALL_TIME, 'Install Time'],
    [
      ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
      'Client Version'
    ],
    [
      ForemanIntegerClientRuleForemanIntegerField.LAST_BOOT_TIME,
      'Last Boot Time'
    ],
    [ForemanIntegerClientRuleForemanIntegerField.CLIENT_CLOCK, 'Client Clock'],
    [ForemanIntegerClientRuleForemanIntegerField.UNSET, 'Unset'],
    [undefined, 'Undefined Condition Field'],

  ]);

  protected clientRateBucket(clientRate: number) {
    if (clientRate === 0) {
      return 'unlimited';
    } else if (clientRate === 200) {
      return 'standard';
    } else {
      return 'custom';
    }
  }
}
