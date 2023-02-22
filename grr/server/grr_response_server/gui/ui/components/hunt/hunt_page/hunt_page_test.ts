import {Location} from '@angular/common';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiHuntState, Browser} from '../../../lib/api/api_interfaces';
import {HttpApiService} from '../../../lib/api/http_api_service';
import {mockHttpApiService} from '../../../lib/api/http_api_service_test_util';
import {translateHuntApproval} from '../../../lib/api_translation/hunt';
import {HuntState} from '../../../lib/models/hunt';
import {newFlowDescriptorMap, newHunt} from '../../../lib/models/model_test_util';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {mockConfigGlobalStore} from '../../../store/config_global_store_test_util';
import {HuntApprovalGlobalStore} from '../../../store/hunt_approval_global_store';
import {mockHuntApprovalGlobalStore} from '../../../store/hunt_approval_global_store_test_util';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';
import {mockHuntPageGlobalStore} from '../../../store/hunt_page_global_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {UserGlobalStore} from '../../../store/user_global_store';
import {mockUserGlobalStore} from '../../../store/user_global_store_test_util';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';
import {NEW_HUNT_ROUTES} from '../new_hunt/routing';

import {HuntPage} from './hunt_page';
import {HuntPageModule} from './module';
import {HUNT_PAGE_ROUTES} from './routing';

initTestEnvironment();

describe('hunt page test', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HuntPageModule,
            RouterTestingModule.withRoutes(
                [...HUNT_PAGE_ROUTES, ...NEW_HUNT_ROUTES]),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
            {provide: HttpApiService, useFactory: mockHttpApiService},
            {provide: UserGlobalStore, useFactory: mockUserGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            HuntPageGlobalStore, {useFactory: mockHuntPageGlobalStore})
        .overrideProvider(
            ConfigGlobalStore, {useFactory: mockConfigGlobalStore})
        .overrideProvider(
            HuntApprovalGlobalStore, {useFactory: mockHuntApprovalGlobalStore})
        .compileComponents();
  }));

  it('selects huntId based on the route', async () => {
    await TestBed.inject(Router).navigate(['hunts/999']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    fixture.detectChanges();

    expect(huntPageLocalStore.selectHunt).toHaveBeenCalledWith('999');
  });

  it('displays hunt overview information - NOT STARTED', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.NOT_STARTED,
      flowName: 'MadeUpFlow',
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('.hunt-overview'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Ghost');
    expect(text).toContain('1984');
    expect(text).toContain('buster');
    expect(text).toContain('Collection not started');
    expect(text).toContain('MadeUpFlow');
    expect(text).toContain('View flow arguments');
    expect(text).toContain('Copy and tweak');
    // hunt state is NOT_STARTED
    expect(text).toContain('Cancel collection');
    expect(text).toContain('Start collection');
  });

  it('displays hunt overview information - PAUSED', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.PAUSED,
      flowName: 'MadeUpFlow',
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('.hunt-overview'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Ghost');
    expect(text).toContain('1984');
    expect(text).toContain('buster');
    expect(text).toContain('Collection paused');
    expect(text).toContain('MadeUpFlow');
    expect(text).toContain('View flow arguments');
    expect(text).toContain('Copy and tweak');
    // hunt state is PAUSED
    expect(text).toContain('Cancel collection');
    expect(text).toContain('Start collection');
  });

  it('displays hunt overview information - STARTED', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.RUNNING,
      flowName: 'MadeUpFlow',
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('.hunt-overview'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Ghost');
    expect(text).toContain('1984');
    expect(text).toContain('buster');
    expect(text).toContain('Collection running');
    expect(text).toContain('left');
    expect(text).toContain('MadeUpFlow');
    expect(text).toContain('View flow arguments');
    expect(text).toContain('Copy and tweak');
    // hunt state is STARTED
    expect(text).toContain('Cancel collection');
    expect(text).not.toContain('Start collection');
  });

  it('displays hunt overview information - CANCELLED', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.CANCELLED,
      flowName: 'MadeUpFlow',
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('.hunt-overview'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Ghost');
    expect(text).toContain('1984');
    expect(text).toContain('buster');
    expect(text).toContain('Collection cancelled');
    expect(text).toContain('MadeUpFlow');
    expect(text).toContain('View flow arguments');
    expect(text).toContain('Copy and tweak');
    // hunt state is CANCELLED
    expect(text).not.toContain('Cancel collection');
    expect(text).not.toContain('Start collection');
  });

  it('expands flow arguments on overview section', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      flowName: 'CollectBrowserHistory',
      flowArgs: {
        '@type':
            'type.googleapis.com/grr.CollectBrowserHistoryArgs',
        'browsers': [Browser.CHROME]
      },
    }));
    const configGlobalStore =
        injectMockStore(ConfigGlobalStore, fixture.debugElement);
    configGlobalStore.mockedObservables.flowDescriptors$.next(
        newFlowDescriptorMap({
          name: 'CollectBrowserHistory',
          friendlyName: 'Browser History',
        }));
    fixture.detectChanges();

    const showFlowParams =
        fixture.debugElement.query(By.css('.flow-params-button'));
    showFlowParams.nativeElement.click();
    fixture.detectChanges();

    const args = fixture.debugElement.query(By.css('.collapsed-info'));
    const text = args.nativeElement.textContent;
    expect(text).toContain('Browser History');
    expect(text).toContain('Chrome');
    expect(text).toContain('Firefox');

    expect(text).toContain('Hide flow arguments');
  });

  it('Cancel button calls cancelHunt with correct state', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.RUNNING,
    }));
    fixture.detectChanges();

    const cancelButton =
        fixture.debugElement.query(By.css('button[name=cancel-button]'));
    cancelButton.nativeElement.click();
    expect(huntPageLocalStore.cancelHunt).toHaveBeenCalledTimes(1);
  });

  it('Start button calls startHunt with correct state', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      huntId: '1984',
      description: 'Ghost',
      creator: 'buster',
      state: HuntState.PAUSED,
    }));
    fixture.detectChanges();

    const startButton =
        fixture.debugElement.query(By.css('button[name=start-button]'));
    startButton.nativeElement.click();
    expect(huntPageLocalStore.startHunt).toHaveBeenCalledTimes(1);
  });

  it('displays hunt progress information', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();
    const huntPageLocalStore =
        injectMockStore(HuntPageGlobalStore, fixture.debugElement);
    huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
      allClientsCount: BigInt(10),
      completedClientsCount: BigInt(3),
      remainingClientsCount: BigInt(7),
      clientsWithResultsCount: BigInt(1),
    }));
    fixture.detectChanges();

    const overviewSection =
        fixture.debugElement.query(By.css('app-hunt-progress'));
    const text = overviewSection.nativeElement.textContent;
    expect(text).toContain('Total progress');
    expect(text).toContain('~ 10 clients');
    expect(text).toContain('30 %');  // Complete
    expect(text).toContain('70 %');  // In progress
    expect(text).toContain('20 %');  // No results
    expect(text).toContain('10 %');  // With results
  });

  it('Copy button navigatest to new hunt page with correct param',
     fakeAsync(async () => {
       await TestBed.inject(Router).navigate(['hunts/1984']);
       const location: Location = TestBed.inject(Location);

       const fixture = TestBed.createComponent(HuntPage);
       fixture.detectChanges();
       const huntPageLocalStore =
           injectMockStore(HuntPageGlobalStore, fixture.debugElement);
       huntPageLocalStore.mockedObservables.selectedHunt$.next(newHunt({
         huntId: '1984',
         description: 'Ghost',
         creator: 'buster',
         state: HuntState.RUNNING,
       }));
       fixture.detectChanges();

       const copyHuntButton =
           fixture.debugElement.query(By.css('button[name=copy-button]'));
       copyHuntButton.nativeElement.click();

       fixture.detectChanges();
       tick();  // after tick(), URL changes will have taken into effect.

       expect(location.path()).toBe('/new-hunt?huntId=1984');
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

  it('displays correct approval information on card', async () => {
    await TestBed.inject(Router).navigate(['hunts/1984']);
    const fixture = TestBed.createComponent(HuntPage);
    fixture.detectChanges();

    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'approver',
      canaryMode: false,
      huntApprovalRequired: true,
    });
    fixture.detectChanges();

    injectMockStore(HuntApprovalGlobalStore)
        .mockedObservables.latestApproval$.next(translateHuntApproval({
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
        }));
    fixture.detectChanges();

    expect(fixture.componentInstance.approvalCard).toBeDefined();
    expect(fixture.nativeElement.textContent).toContain('b');
    expect(fixture.nativeElement.textContent).toContain('c');
    expect(fixture.nativeElement.textContent).toContain('Pending reason');
    expect(fixture.nativeElement.textContent).toContain('Send new request');
  });
});
