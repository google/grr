import {HttpErrorResponse} from '@angular/common/http';
import {TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {Browser, ForemanClientRuleSetMatchMode, ForemanClientRuleType, ForemanIntegerClientRuleForemanIntegerField, ForemanIntegerClientRuleOperator, ForemanLabelClientRuleMatchMode, ForemanRegexClientRuleForemanStringField} from '../../../lib/api/api_interfaces';
import {ApiModule} from '../../../lib/api/module';
import {RequestStatusType} from '../../../lib/api/track_request';
import {newFlowDescriptorMap, newHunt, newHuntApproval, newSafetyLimits} from '../../../lib/models/model_test_util';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../../store/config_global_store_test_util';
import {HuntApprovalPageGlobalStore} from '../../../store/hunt_approval_page_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {UserGlobalStore} from '../../../store/user_global_store';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';

import {HuntApprovalPage} from './hunt_approval_page';
import {HuntApprovalPageModule} from './hunt_approval_page_module';
import {HUNT_APPROVAL_PAGE_ROUTES} from './routing';



initTestEnvironment();

describe('HuntApprovalPage Component', () => {
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(async () => {
    configGlobalStore = mockConfigGlobalStore();

    await TestBed
        .configureTestingModule({
          imports: [
            RouterTestingModule.withRoutes(HUNT_APPROVAL_PAGE_ROUTES),
            ApiModule,
            NoopAnimationsModule,
            HuntApprovalPageModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    await TestBed.inject(Router).navigate(
        ['hunts/hid/users/req/approvals/aid']);
  });

  it('should be created', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    expect(fixture.nativeElement).toBeTruthy();
  });

  it('loads approval information on route change', async () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    expect(injectMockStore(HuntApprovalPageGlobalStore).selectHuntApproval)
        .toHaveBeenCalledWith(
            {huntId: 'hid', requestor: 'req', approvalId: 'aid'});
  });

  it('displays approval information on hunt change', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap({
          name: 'CollectBrowserHistory',
          friendlyName: 'Collects Browser History',
          category: 'b',
          defaultArgs: {},
        }));

    const TWO_DAYS = 2 * 24 * 60 * 60;

    injectMockStore(HuntApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newHuntApproval({
          subject: newHunt({
            name: 'Get_free_bitcoin',
            description: 'testing',
            huntId: '1234',
            flowName: 'CollectBrowserHistory',
            flowArgs: {
              '@type':
                  'type.googleapis.com/grr.CollectBrowserHistoryArgs',
              'browsers': [Browser.CHROME]
            },
            created: new Date('2/1/22'),
            safetyLimits: newSafetyLimits({
              clientRate: 200,
              clientLimit: BigInt(0),
              avgResultsPerClientLimit: BigInt(20),
              avgCpuSecondsPerClientLimit: BigInt(40),
              avgNetworkBytesPerClientLimit: BigInt(80),
              cpuLimit: BigInt(60 * 2),
              networkBytesLimit: BigInt(60),
              expiryTime: BigInt(TWO_DAYS),
            }),
          }),
          requestor: 'testuser',
          reason: 'I am dummy reason',
          requestedApprovers: ['a', 'b'],
          status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
          approvers: ['approver1', 'approver2'],
        }));
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Get_free_bitcoin');
    expect(text).toContain('testing');
    expect(text).toContain('1234');
    expect(text).toContain('All matching clients');
    expect(text).toContain('200');
    expect(text).toContain('standard');
    expect(text).toContain('CollectBrowserHistory');
    expect(text).toContain('Chrome');
    expect(text).toContain('20');
    expect(text).toContain('40 s');
    expect(text).toContain('80 B');
    expect(text).toContain('2 minutes');
    expect(text).toContain('60 B');
    expect(text).toContain('2 days');
    expect(text).toContain('2022');
    expect(text).toContain('I am dummy reason');
    expect(text).toContain('testuser');
    expect(text).toContain('a');
    expect(text).toContain('b');
    expect(text).toContain('pending');
    expect(text).toContain('approver1');
    expect(text).toContain('approver2');
  });

  it('grants approval on button click', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    const huntApprovalPageGlobalStore =
        injectMockStore(HuntApprovalPageGlobalStore);

    huntApprovalPageGlobalStore.mockedObservables.approval$.next(
        newHuntApproval({
          huntId: '1234',
          requestor: 'msan',
          reason: 'foobazzle 42',
          status: {type: 'pending', reason: 'testing reason'},
        }));
    fixture.detectChanges();

    expect(huntApprovalPageGlobalStore.grantApproval).not.toHaveBeenCalled();
    fixture.debugElement.query(By.css('mat-card-actions button'))
        .triggerEventHandler('click', undefined);
    expect(huntApprovalPageGlobalStore.grantApproval).toHaveBeenCalled();
  });

  it('shows a progress spinner when the approval request is in flight', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    const huntApprovalPageGlobalStore =
        injectMockStore(HuntApprovalPageGlobalStore);
    huntApprovalPageGlobalStore.mockedObservables.approval$.next(
        newHuntApproval({
          huntId: '1234',
          requestor: 'msan',
          reason: 'foobazzle 42',
        }));
    fixture.detectChanges();


    expect(fixture.debugElement.query(By.css('button mat-spinner'))).toBeNull();

    huntApprovalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        {status: RequestStatusType.SENT});
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button mat-spinner')))
        .not.toBeNull();

    huntApprovalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.ERROR,
      error: new HttpErrorResponse({error: ''})
    });
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('button mat-spinner'))).toBeNull();
  });

  it('disables the grant button when a grant request is in flight', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    const huntApprovalPageGlobalStore =
        injectMockStore(HuntApprovalPageGlobalStore);
    huntApprovalPageGlobalStore.mockedObservables.approval$.next(
        newHuntApproval({
          huntId: '1234',
          requestor: 'msan',
          reason: 'foobazzle 42',
        }));
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    huntApprovalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        undefined);
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBeFalsy();

    huntApprovalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        {status: RequestStatusType.SENT});
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBe('true');

    huntApprovalPageGlobalStore.mockedObservables.grantRequestStatus$.next({
      status: RequestStatusType.ERROR,
      error: new HttpErrorResponse({error: ''})
    });
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBeFalsy();
  });

  it('disables the grant button if the current user approved already', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    const approvalPageGlobalStore =
        injectMockStore(HuntApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(newHuntApproval({
      huntId: '1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      approvers: ['somebodyelse'],
    }));
    injectMockStore(UserGlobalStore)
        .mockedObservables.currentUser$.next(
            {name: 'approver', canaryMode: false, huntApprovalRequired: false});
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        undefined);
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBeFalsy();

    approvalPageGlobalStore.mockedObservables.approval$.next(newHuntApproval({
      huntId: '1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      approvers: ['approver'],
    }));
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBe('true');
  });

  it('disables the grant button if the approval is already granted', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    const approvalPageGlobalStore =
        injectMockStore(HuntApprovalPageGlobalStore);
    approvalPageGlobalStore.mockedObservables.approval$.next(newHuntApproval({
      huntId: '1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      status: {type: 'pending', reason: 'testing reason'},
    }));
    injectMockStore(UserGlobalStore)
        .mockedObservables.currentUser$.next(
            {name: 'approver', canaryMode: false, huntApprovalRequired: false});
    approvalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        undefined);
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBeFalsy();

    approvalPageGlobalStore.mockedObservables.approval$.next(newHuntApproval({
      huntId: '1234',
      requestor: 'msan',
      reason: 'foobazzle 42',
      status: {type: 'valid'},

    }));
    fixture.detectChanges();

    expect(grantButton.attributes['disabled']).toBe('true');
  });

  it('disables the grant button if the current user is the requestor', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    const huntApprovalPageGlobalStore =
        injectMockStore(HuntApprovalPageGlobalStore);
    huntApprovalPageGlobalStore.mockedObservables.approval$.next(
        newHuntApproval({
          huntId: '1234',
          requestor: 'requestor',
          reason: 'foobazzle 42',
          approvers: ['somebodyelse'],
        }));
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'requestor',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    huntApprovalPageGlobalStore.mockedObservables.grantRequestStatus$.next(
        undefined);
    fixture.detectChanges();

    const grantButton = fixture.debugElement.query(By.css('.grant-button'));

    expect(grantButton.attributes['disabled']).toBe('true');
  });

  it('shows "New Configuration" when hunt is new', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    injectMockStore(HuntApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newHuntApproval({
          subject: newHunt({
            name: 'Get_free_bitcoin',
            description: 'testing',
            huntId: '1234',
            huntReference: undefined,
            flowReference: undefined,
          }),
          requestor: 'msan',
          reason: 'foobazzle 42',
        }));

    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('New Configuration');
  });

  it('does not show "New Configuration" when hunt is based on old hunt', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    injectMockStore(HuntApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newHuntApproval({
          subject: newHunt({
            name: 'Get_free_bitcoin',
            description: 'testing',
            huntId: '1234',
            huntReference: {huntId: '4321'},
            flowReference: undefined,
          }),
          requestor: 'msan',
          reason: 'foobazzle 42',
        }));

    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).not.toContain('New Configuration');
  });

  it('does not show "New Configuration" when hunt is based on a flow', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    injectMockStore(HuntApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newHuntApproval({
          subject: newHunt({
            name: 'Get_free_bitcoin',
            description: 'testing',
            huntId: '1234',
            huntReference: undefined,
            flowReference: {flowId: '4321', clientId: 'C.1234'},
          }),
          requestor: 'msan',
          reason: 'foobazzle 42',
        }));

    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).not.toContain('New Configuration');
  });

  it('displays flowName as a link to flowReference', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    injectMockStore(HuntApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newHuntApproval({
          subject: newHunt({
            name: 'Get_free_bitcoin',
            description: 'testing',
            huntId: '1234',
            flowName: 'CollectBrowserHistory',
            flowReference: {flowId: '0C1DAF7B93B10ACB', clientId: 'C.1234'},
          }),
          requestor: 'msan',
          reason: 'foobazzle 42',
        }));
    fixture.detectChanges();

    const link = fixture.debugElement.query(By.css('a'));
    expect(link.attributes['href'])
        .toContain('clients/C.1234/flows/0C1DAF7B93B10ACB');
    expect(link.nativeElement.textContent).toContain('CollectBrowserHistory');

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('0C1DAF7B93B10ACB');
  });

  it('displays selected clients correctly', () => {
    const fixture = TestBed.createComponent(HuntApprovalPage);
    fixture.detectChanges();

    injectMockStore(HuntApprovalPageGlobalStore)
        .mockedObservables.approval$.next(newHuntApproval({
          subject: newHunt({
            clientRuleSet: {
              matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
              rules: [
                {
                  ruleType: ForemanClientRuleType.OS,
                  os: {osWindows: true},
                },
                {
                  ruleType: ForemanClientRuleType.LABEL,
                  label: {
                    labelNames: ['test-label-1,test-label-2'],
                    matchMode: ForemanLabelClientRuleMatchMode.MATCH_ANY,
                  },
                },
                {
                  ruleType: ForemanClientRuleType.REGEX,
                  regex: {
                    attributeRegex: 'user1 user2',
                    field:
                        ForemanRegexClientRuleForemanStringField.CLIENT_LABELS,
                  }
                },
                {
                  ruleType: ForemanClientRuleType.INTEGER,
                  integer: {
                    operator: ForemanIntegerClientRuleOperator.LESS_THAN,
                    value: '123',
                    field: ForemanIntegerClientRuleForemanIntegerField
                               .INSTALL_TIME,
                  }
                }
              ],
            }
          }),
        }));
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('match all (and)');

    expect(text).toContain('Operating System');
    expect(text).toContain('Windows');
    expect(text).not.toContain('Linux');

    expect(text).toContain('Label');
    expect(text).toContain('match any');
    expect(text).toContain('test-label-1');
    expect(text).toContain('test-label-2');

    expect(text).toContain('Client Labels');
    expect(text).toContain('user1 user2');

    expect(text).toContain('Install Time');
    expect(text).toContain('Less Than:');
    expect(text).toContain('123');
  });
});
