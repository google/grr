import {Location} from '@angular/common';
import {
  TestBed,
  discardPeriodicTasks,
  fakeAsync,
  tick,
  waitForAsync,
} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {
  ApiHuntError,
  ApiHuntResult,
  ApiHuntState,
  Browser,
} from '../../../lib/api/api_interfaces';
import {HttpApiService} from '../../../lib/api/http_api_service';
import {mockHttpApiService} from '../../../lib/api/http_api_service_test_util';
import {translateHuntApproval} from '../../../lib/api_translation/hunt';
import {getFlowTitleFromFlowName} from '../../../lib/models/flow';
import {HuntState, getHuntTitle} from '../../../lib/models/hunt';
import {
  newFlowDescriptorMap,
  newHunt,
} from '../../../lib/models/model_test_util';
import {PayloadType} from '../../../lib/models/result';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {mockConfigGlobalStore} from '../../../store/config_global_store_test_util';
import {HuntApprovalLocalStore} from '../../../store/hunt_approval_local_store';
import {mockHuntApprovalLocalStore} from '../../../store/hunt_approval_local_store_test_util';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';
import {mockHuntPageGlobalStore} from '../../../store/hunt_page_global_store_test_util';
import {HuntResultDetailsGlobalStore} from '../../../store/hunt_result_details_global_store';
import {
  HuntResultDetailsGlobalStoreMock,
  mockHuntResultDetailsGlobalStore,
} from '../../../store/hunt_result_details_global_store_test_util';
import {
  STORE_PROVIDERS,
  injectMockStore,
} from '../../../store/store_test_providers';
import {UserGlobalStore} from '../../../store/user_global_store';
import {mockUserGlobalStore} from '../../../store/user_global_store_test_util';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';
import {HUNT_ROUTES} from '../../app/routing';

import {HuntPage} from './hunt_page';
import {HuntPageModule} from './module';

initTestEnvironment();

const TEST_HUNT = newHunt({
  huntId: '1984',
  description: 'Ghost',
  creator: 'buster',
  created: new Date('1970-01-12 13:46:39 UTC'),
  initStartTime: new Date('1980-01-12 13:46:39 UTC'),
  lastStartTime: undefined,
  flowName: 'MadeUpFlow',
  resourceUsage: {
    totalCPUTime: 0.7999999821186066,
    totalNetworkTraffic: BigInt(94545),
  },
});

async function createHuntPageWithState(state: HuntState) {
  await TestBed.inject(Router).navigate(['hunts/1984']);
  const fixture = TestBed.createComponent(HuntPage);
  fixture.detectChanges();
  const huntPageLocalStore = injectMockStore(
    HuntPageGlobalStore,
    fixture.debugElement,
  );
  const hunt = {...TEST_HUNT, state};
  huntPageLocalStore.mockedObservables.selectedHunt$.next(hunt);
  fixture.detectChanges();

  return {fixture, huntPageLocalStore};
}

describe('hunt page test', () => {
  const httpApiService = mockHttpApiService();
  let huntResultDetailsGlobalStore: HuntResultDetailsGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    huntResultDetailsGlobalStore = mockHuntResultDetailsGlobalStore();

    TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        HuntPageModule,
        RouterTestingModule.withRoutes([...HUNT_ROUTES]),
      ],
      providers: [
        ...STORE_PROVIDERS,
        {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
        {provide: HttpApiService, useFactory: () => httpApiService},
        {provide: UserGlobalStore, useFactory: mockUserGlobalStore},
        {
          provide: HuntResultDetailsGlobalStore,
          useFactory: () => huntResultDetailsGlobalStore,
        },
      ],
      teardown: {destroyAfterEach: false},
    })
      .overrideProvider(HuntPageGlobalStore, {
        useFactory: mockHuntPageGlobalStore,
      })
      .overrideProvider(ConfigGlobalStore, {useFactory: mockConfigGlobalStore})
      .overrideProvider(HuntApprovalLocalStore, {
        useFactory: mockHuntApprovalLocalStore,
      })
      .compileComponents();
  }));

  it('selects huntId based on the route', async () => {
    await TestBed.inject(Router).navigate(['hunts/999']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore = injectMockStore(
      HuntPageGlobalStore,
      fixture.debugElement,
    );
    fixture.detectChanges();

    expect(huntPageLocalStore.selectHunt).toHaveBeenCalledWith('999');
  });

  it('displays basic hunt overview information', async () => {
    const fixture = (await createHuntPageWithState(HuntState.NOT_STARTED))
      .fixture;

    const huntOverviewLink = fixture.debugElement.query(
      By.css('title-editor a'),
    );
    expect(huntOverviewLink.attributes['href']).toBe('/hunts');

    const overviewSection = fixture.debugElement.query(
      By.css('.hunt-overview'),
    );
    expect(
      overviewSection.query(By.css('title-editor')).nativeElement.textContent,
    ).toContain(getHuntTitle(TEST_HUNT));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('1984');
    expect(text).toContain('buster');
    expect(text).toContain('1970-01-12 13:46:39 UTC');
    expect(text).toContain('1980-01-12 13:46:39 UTC');
    expect(text).toContain('never started');
    expect(text).toContain('MadeUpFlow');
    expect(text).toContain('View flow arguments');
    expect(text).toContain('1 s');
    expect(text).toContain('92.32 KiB');
  });

  describe('displays correct status chip', () => {
    it('not started', async () => {
      const fixture = (await createHuntPageWithState(HuntState.NOT_STARTED))
        .fixture;
      const statusChip = fixture.debugElement.query(
        By.css('.hunt-overview app-hunt-status-chip'),
      );
      expect(statusChip.nativeElement.textContent).toContain(
        'Collection not started',
      );
    });

    it('client limit', async () => {
      const fixture = (
        await createHuntPageWithState(HuntState.REACHED_CLIENT_LIMIT)
      ).fixture;
      const statusChip = fixture.debugElement.query(
        By.css('.hunt-overview app-hunt-status-chip'),
      );
      expect(statusChip.nativeElement.textContent).toContain(
        'Reached client limit  (200 clients)',
      );
    });

    it('running', async () => {
      const fixture = (await createHuntPageWithState(HuntState.RUNNING))
        .fixture;
      const statusChip = fixture.debugElement.query(
        By.css('.hunt-overview app-hunt-status-chip'),
      );
      expect(statusChip.nativeElement.textContent).toContain(
        'Collection running',
      );
    });

    it('cancelled', async () => {
      const fixture = (await createHuntPageWithState(HuntState.CANCELLED))
        .fixture;
      const statusChip = fixture.debugElement.query(
        By.css('.hunt-overview app-hunt-status-chip'),
      );
      expect(statusChip.nativeElement.textContent).toContain(
        'Collection cancelled',
      );
    });

    it('client limit', async () => {
      const fixture = (
        await createHuntPageWithState(HuntState.REACHED_TIME_LIMIT)
      ).fixture;
      const statusChip = fixture.debugElement.query(
        By.css('.hunt-overview app-hunt-status-chip'),
      );
      expect(statusChip.nativeElement.textContent).toContain(
        'Reached time limit   (32 seconds)',
      );
    });
  });

  describe('displays correct actions', () => {
    it('not started', async () => {
      const fixture = (await createHuntPageWithState(HuntState.NOT_STARTED))
        .fixture;
      const actionsText = fixture.debugElement.query(
        By.css('.hunt-overview .actions'),
      ).nativeElement.textContent;
      expect(actionsText).toContain('Copy and tweak');
      expect(actionsText).toContain('Cancel collection');
      expect(actionsText).toContain('Start collection');
      expect(actionsText).toContain('Change rollout parameters and start');
    });

    it('paused', async () => {
      const fixture = (
        await createHuntPageWithState(HuntState.REACHED_CLIENT_LIMIT)
      ).fixture;
      const actionsText = fixture.debugElement.query(
        By.css('.hunt-overview .actions'),
      ).nativeElement.textContent;
      expect(actionsText).toContain('Copy and tweak');
      expect(actionsText).toContain('Cancel collection');
      expect(actionsText).not.toContain('Restart collection');
      expect(actionsText).toContain('Change rollout parameters and continue');
    });

    it('running', async () => {
      const fixture = (await createHuntPageWithState(HuntState.RUNNING))
        .fixture;
      const actionsText = fixture.debugElement.query(
        By.css('.hunt-overview .actions'),
      ).nativeElement.textContent;
      expect(actionsText).toContain('Copy and tweak');
      expect(actionsText).toContain('Cancel collection');
      expect(actionsText).not.toContain('Start collection');
      expect(actionsText).not.toContain(
        'Change rollout parameters and continue',
      );
    });

    it('cancelled', async () => {
      const fixture = (await createHuntPageWithState(HuntState.CANCELLED))
        .fixture;
      const actionsText = fixture.debugElement.query(
        By.css('.hunt-overview .actions'),
      ).nativeElement.textContent;
      expect(actionsText).toContain('Copy and tweak');
      expect(actionsText).not.toContain('Cancel collection');
      expect(actionsText).not.toContain('Start collection');
      expect(actionsText).not.toContain(
        'Change rollout parameters and continue',
      );
    });

    it('completed', async () => {
      const fixture = (
        await createHuntPageWithState(HuntState.REACHED_TIME_LIMIT)
      ).fixture;
      const actionsText = fixture.debugElement.query(
        By.css('.hunt-overview .actions'),
      ).nativeElement.textContent;
      expect(actionsText).toContain('Copy and tweak');
      expect(actionsText).not.toContain('Cancel collection');
      expect(actionsText).not.toContain('Restart collection');
      expect(actionsText).not.toContain(
        'Change rollout parameters and continue',
      );
    });
  });

  it('expands flow arguments on overview section', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore = injectMockStore(
      HuntPageGlobalStore,
      fixture.debugElement,
    );
    const flowName = 'CollectBrowserHistory';
    huntPageLocalStore.mockedObservables.selectedHunt$.next(
      newHunt({
        flowName,
        flowArgs: {
          '@type':
            'type.googleapis.com/grr.CollectBrowserHistoryArgs',
          'browsers': [Browser.CHROME],
        },
      }),
    );
    const configGlobalStore = injectMockStore(
      ConfigGlobalStore,
      fixture.debugElement,
    );
    configGlobalStore.mockedObservables.flowDescriptors$.next(
      newFlowDescriptorMap({
        name: flowName,
        friendlyName: 'Browser History',
      }),
    );
    fixture.detectChanges();

    const showFlowParams = fixture.debugElement.query(
      By.css('.flow-params-button'),
    );
    showFlowParams.nativeElement.click();
    fixture.detectChanges();

    const args = fixture.debugElement.query(By.css('.collapsed-info'));
    const text = args.nativeElement.textContent;
    expect(text).toContain(getFlowTitleFromFlowName(flowName));
    expect(text).toContain('Chrome');
    expect(text).toContain('Firefox');

    expect(text).toContain('Hide flow arguments');
  });

  it('Cancel button calls cancelHunt with correct state', async () => {
    const testData = await createHuntPageWithState(HuntState.RUNNING);
    const fixture = testData.fixture;
    const huntPageLocalStore = testData.huntPageLocalStore;

    const cancelButton = fixture.debugElement.query(
      By.css('button[name=cancel-button]'),
    );
    cancelButton.nativeElement.click();
    expect(huntPageLocalStore.cancelHunt).toHaveBeenCalledTimes(1);
  });

  it('Start button calls startHunt with correct state', async () => {
    const testData = await createHuntPageWithState(HuntState.NOT_STARTED);
    const fixture = testData.fixture;
    const huntPageLocalStore = testData.huntPageLocalStore;

    const startButton = fixture.debugElement.query(
      By.css('button[name=start-button]'),
    );
    startButton.nativeElement.click();
    expect(huntPageLocalStore.startHunt).toHaveBeenCalledTimes(1);
  });

  it('Cancel and Start buttons are disabled when no access', async () => {
    const fixture = (await createHuntPageWithState(HuntState.NOT_STARTED))
      .fixture;
    const huntApprovalLocalStore = injectMockStore(
      HuntApprovalLocalStore,
      fixture.debugElement,
    );
    huntApprovalLocalStore.mockedObservables.hasAccess$.next(false);
    fixture.detectChanges();

    const cancelButton = fixture.debugElement.query(
      By.css('button[name=cancel-button]'),
    );
    expect(cancelButton.nativeElement.disabled).toBe(true);
    const startButton = fixture.debugElement.query(
      By.css('button[name=start-button]'),
    );
    expect(startButton.nativeElement.disabled).toBe(true);
  });

  it('does not display progress/results when not started', async () => {
    const fixture = (await createHuntPageWithState(HuntState.NOT_STARTED))
      .fixture;

    expect(fixture.debugElement.query(By.css('app-hunt-progress'))).toBeNull();
    expect(fixture.debugElement.query(By.css('app-hunt-results'))).toBeNull();
  });

  it('displays progress/results when other state', async () => {
    const fixture = (
      await createHuntPageWithState(HuntState.REACHED_CLIENT_LIMIT)
    ).fixture;

    expect(
      fixture.debugElement.query(By.css('app-hunt-progress')),
    ).toBeTruthy();
    expect(fixture.debugElement.query(By.css('app-hunt-results'))).toBeTruthy();
  });

  it('displays hunt progress information', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore = injectMockStore(
      HuntPageGlobalStore,
      fixture.debugElement,
    );
    huntPageLocalStore.mockedObservables.selectedHunt$.next(
      newHunt({
        allClientsCount: BigInt(10),
        completedClientsCount: BigInt(3),
        remainingClientsCount: BigInt(7),
        clientsWithResultsCount: BigInt(1),
      }),
    );
    fixture.detectChanges();

    const overviewSection = fixture.debugElement.query(
      By.css('app-hunt-progress'),
    );
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Total progress');
    expect(text).toContain('~ 10 clients');
    expect(text).toContain('30 %'); // Complete
    expect(text).toContain('70 %'); // In progress
    expect(text).toContain('20 %'); // No results
    expect(text).toContain('10 %'); // With results
  });

  it('modify hunt button navigates to modify hunt drawer', fakeAsync(async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const location: Location = TestBed.inject(Location);

    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore = injectMockStore(
      HuntPageGlobalStore,
      fixture.debugElement,
    );
    huntPageLocalStore.mockedObservables.selectedHunt$.next(
      newHunt({
        huntId: '1984',
        description: 'Ghost',
        creator: 'buster',
        state: HuntState.REACHED_CLIENT_LIMIT,
      }),
    );
    fixture.detectChanges();

    const modifyHuntButton = fixture.debugElement.query(
      By.css('a[name=modify-button]'),
    );
    modifyHuntButton.nativeElement.click();

    fixture.detectChanges();
    tick(); // after tick(), URL changes will have taken into effect.

    expect(location.path()).toBe('/hunts/1984(drawer:modify-hunt)');
    discardPeriodicTasks();
  }));

  it('Copy button navigates to new hunt page with correct param', fakeAsync(async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const location: Location = TestBed.inject(Location);

    const fixture = (await createHuntPageWithState(HuntState.RUNNING)).fixture;

    const copyHuntButton = fixture.debugElement.query(
      By.css('button[name=copy-button]'),
    );
    copyHuntButton.nativeElement.click();

    fixture.detectChanges();
    tick(); // after tick(), URL changes will have taken into effect.

    expect(location.path()).toBe('/new-hunt?huntId=1984');

    discardPeriodicTasks();
  }));

  it('does not display approval component if disabled', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalCard).toBe(undefined);

    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalCard).toBe(undefined);
  });

  it('displays approval component if enabled', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalCard).toBe(undefined);

    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: true,
    });
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalCard).toBeDefined();
  });

  it('displays correct approval information on card', fakeAsync(async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: true,
    });
    const huntApprovalLocalStore = injectMockStore(
      HuntApprovalLocalStore,
      fixture.debugElement,
    );
    huntApprovalLocalStore.mockedObservables.latestApproval$.next(
      translateHuntApproval({
        subject: {
          huntId: 'hunt_1234',
          creator: 'creator',
          name: 'name',
          state: ApiHuntState.PAUSED,
          created: '12345',
          huntRunnerArgs: {clientRate: 0},
          flowArgs: {},
          flowName: 'name',
        },
        id: '2',
        reason: 'Pending reason',
        requestor: 'requestor',
        isValid: false,
        isValidMessage: 'Need at least 1 more approvers.',
        approvers: ['approver'],
        notifiedUsers: ['b', 'c'],
      }),
    );
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalCard).toBeDefined();
    expect(fixture.nativeElement.textContent).toContain('b');
    expect(fixture.nativeElement.textContent).toContain('c');
    expect(fixture.nativeElement.textContent).toContain('Pending reason');
    expect(fixture.nativeElement.textContent).toContain('Send new request');
  }));

  it('Hides approval card content by default if there is no approval', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: true,
    });
    injectMockStore(
      HuntApprovalLocalStore,
    ).mockedObservables.latestApproval$.next(null);
    fixture.detectChanges();

    const approvalCard = fixture.componentInstance.approvalCard;
    expect(approvalCard).toBeDefined();

    const approvalCardContent = fixture.debugElement.query(
      By.css('approval-card .content'),
    );
    expect(approvalCardContent.nativeNode.clientHeight).toBe(0);
  });

  it('Does not close the approval card after receiving a polled empty-approval', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();

    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: true,
    });
    const mockHuntApprovalStore = injectMockStore(HuntApprovalLocalStore);
    mockHuntApprovalStore.mockedObservables.latestApproval$.next(null);
    fixture.detectChanges();

    const approvalCard = fixture.componentInstance.approvalCard;
    expect(approvalCard).toBeDefined();

    const approvalCardContent = fixture.debugElement.query(
      By.css('approval-card .content'),
    );
    expect(approvalCardContent.nativeNode.clientHeight).toBe(0);

    const approvalCardHeader = fixture.debugElement.query(
      By.css('approval-card .header'),
    );
    expect(approvalCardHeader).toBeDefined();

    approvalCardHeader.nativeElement.click();
    fixture.detectChanges();

    expect(approvalCardContent.nativeNode.clientHeight).not.toBe(0);

    mockHuntApprovalStore.mockedObservables.latestApproval$.next(null);
    fixture.detectChanges();

    expect(approvalCardContent.nativeNode.clientHeight).not.toBe(0);
  });

  describe('Hunt Result/Error selection', () => {
    it('catches the hunt result selection event', () => {
      const fixture = TestBed.createComponent(HuntPage);
      const component = fixture.componentInstance;

      component.huntId = TEST_HUNT.huntId;

      const huntPageLocalStore = injectMockStore(
        HuntPageGlobalStore,
        fixture.debugElement,
      );

      huntPageLocalStore.mockedObservables.selectedHunt$.next(TEST_HUNT);
      huntPageLocalStore.mockedObservables.huntResultTabs$.next([
        {
          tabName: 'User',
          totalResultsCount: 1,
          payloadType: PayloadType.USER,
        },
      ]);

      fixture.detectChanges();

      const mockHuntResult = {
        'clientId': 'C.1234',
        'payload': {
          'foo': 'bar',
        },
        'payloadType': PayloadType.USER,
        'timestamp': '1',
      };

      // We provide a mock response for the Hunt Results Local Store:
      httpApiService.mockedObservables.listResultsForHunt.next([
        mockHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);
      expect(rows[0].innerText).toContain('View details');

      const eventListenerSpy = spyOn(
        component,
        'openHuntResultDetailsInDrawer',
      );

      fixture.nativeElement.querySelector('.view-details-button').click();

      fixture.detectChanges();

      expect(eventListenerSpy).toHaveBeenCalledWith({
        value: mockHuntResult,
        payloadType: PayloadType.USER,
      });
    });

    it('catches the hunt error selection event', () => {
      const fixture = TestBed.createComponent(HuntPage);
      const component = fixture.componentInstance;

      component.huntId = TEST_HUNT.huntId;

      const huntPageLocalStore = injectMockStore(
        HuntPageGlobalStore,
        fixture.debugElement,
      );

      huntPageLocalStore.mockedObservables.selectedHunt$.next(TEST_HUNT);
      huntPageLocalStore.mockedObservables.huntResultTabs$.next([
        {
          tabName: 'Errors',
          totalResultsCount: 1,
          payloadType: PayloadType.API_HUNT_ERROR,
        },
      ]);

      fixture.detectChanges();

      const mockHuntError: ApiHuntError = {
        clientId: 'C.mockClientId',
        timestamp: '1669027009243432',
        backtrace: 'fooTrace',
        logMessage: 'Something went wrong.',
      };

      // We provide a mock response for the Hunt Results Local Store:
      httpApiService.mockedObservables.listErrorsForHunt.next([mockHuntError]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);
      expect(rows[0].innerText).toContain('View details');

      const eventListenerSpy = spyOn(
        component,
        'openHuntResultDetailsInDrawer',
      );

      fixture.nativeElement.querySelector('.view-details-button').click();

      fixture.detectChanges();

      expect(eventListenerSpy).toHaveBeenCalledWith({
        value: mockHuntError,
        payloadType: PayloadType.API_HUNT_ERROR,
      });
    });

    it('navigates to route and selects result on store', () => {
      const fixture = TestBed.createComponent(HuntPage);
      const component = fixture.componentInstance;
      const router = TestBed.inject(Router);

      component.huntId = '1234ABCD';

      fixture.detectChanges();

      const mockResult: ApiHuntResult = {
        'clientId': 'C.1234',
        'payload': {
          'foo': 'bar',
        },
        'timestamp': '1',
      };

      const mockResultKey = 'C.1234-1234ABCD-1';

      const navigateSpy = spyOn(router, 'navigate');

      component.openHuntResultDetailsInDrawer({
        value: mockResult,
        payloadType: PayloadType.USER,
      });

      expect(navigateSpy).toHaveBeenCalledWith([
        {
          outlets: {
            'drawer': `result-details/${mockResultKey}/${PayloadType.USER}`,
          },
        },
      ]);

      expect(
        huntResultDetailsGlobalStore.selectHuntResultOrError,
      ).toHaveBeenCalledWith(mockResult, component.huntId);
    });

    it('navigates to route and selects error on store', () => {
      const fixture = TestBed.createComponent(HuntPage);
      const component = fixture.componentInstance;
      const router = TestBed.inject(Router);

      component.huntId = '1234ABCD';

      fixture.detectChanges();

      const mockError: ApiHuntError = {
        clientId: 'C.1234',
        timestamp: '1',
        logMessage: 'foo',
        backtrace: 'bar',
      };

      const mockResultKey = 'C.1234-1234ABCD-1';

      const navigateSpy = spyOn(router, 'navigate');

      component.openHuntResultDetailsInDrawer({
        value: mockError,
        payloadType: PayloadType.API_HUNT_ERROR,
      });

      expect(navigateSpy).toHaveBeenCalledWith([
        {
          outlets: {
            'drawer': `result-details/${mockResultKey}/${PayloadType.API_HUNT_ERROR}`,
          },
        },
      ]);

      expect(
        huntResultDetailsGlobalStore.selectHuntResultOrError,
      ).toHaveBeenCalledWith(mockError, component.huntId);
    });
  });
});
