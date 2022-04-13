import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {Component} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {RequestStatusType} from '../../../lib/api/track_request';
import {newFlow} from '../../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../../store/client_page_global_store';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../../store/client_page_global_store_test_util';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../../store/config_global_store_test_util';
import {NewHuntLocalStore} from '../../../store/new_hunt_local_store';
import {mockNewHuntLocalStore} from '../../../store/new_hunt_local_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {UserGlobalStore} from '../../../store/user_global_store';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';

import {NewHuntModule} from './module';
import {NewHunt} from './new_hunt';

initTestEnvironment();

@Component({template: ''})
class TestComponent {
}

describe('new hunt test', () => {
  let configGlobalStore: ConfigGlobalStoreMock;
  let clientPageGlobalStore: ClientPageGlobalStoreMock;
  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();
    clientPageGlobalStore = mockClientPageGlobalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            NewHuntModule,
            RouterTestingModule.withRoutes([
              {path: 'new-hunt', component: NewHunt},
              {path: 'hunts/:id', component: TestComponent}
            ]),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
            {
              provide: ConfigGlobalStore,
              useFactory: () => configGlobalStore,
            },
            {
              provide: ClientPageGlobalStore,
              useFactory: () => clientPageGlobalStore
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            NewHuntLocalStore, {useFactory: mockNewHuntLocalStore})
        .compileComponents();
  }));

  it('loads and displays Flow', async () => {
    await TestBed.inject(Router).navigate(['new-hunt']);

    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();
    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    newHuntLocalStore.mockedObservables.flowWithDescriptor$.next({
      flow: newFlow({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      descriptor: {
        name: 'KeepAlive',
        friendlyName: 'KeepAlive',
        category: 'a',
        defaultArgs: {},
      },
      flowArgType: 'someType',
    });
    fixture.detectChanges();

    const flowSection =
        fixture.debugElement.query(By.css('.new-hunt-container'))
            .query(By.css('.config'));
    const text = flowSection.nativeElement.textContent;
    expect(text).toContain('morty');
    expect(text).toContain('KeepAlive');
  });

  it('sends request approval when child approval component emits the info',
     async () => {
       const fixture = TestBed.createComponent(NewHunt);
       const loader = TestbedHarnessEnvironment.loader(fixture);
       fixture.detectChanges();
       const newHuntLocalStore =
           injectMockStore(NewHuntLocalStore, fixture.debugElement);
       fixture.detectChanges();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: true,
       });
       fixture.detectChanges();

       configGlobalStore.mockedObservables.approvalConfig$.next(
           {optionalCcEmail: 'foo@example.org'});
       fixture.detectChanges();

       const approversInput =
           fixture.debugElement.query(By.css('mat-chip-list input'));
       approversInput.triggerEventHandler('focusin', null);
       fixture.detectChanges();

       clientPageGlobalStore.mockedObservables.approverSuggestions$.next(
           ['user@gmail.com']);
       fixture.detectChanges();

       const input = await loader.getHarness(MatAutocompleteHarness);
       await input.enterText('user');
       const options = await input.getOptions();
       await options[0].click();
       fixture.detectChanges();

       const reason = await loader.getHarness(
           MatInputHarness.with({selector: '[name=reason]'}));
       await reason.setValue('sample reason');
       fixture.detectChanges();
       const button = fixture.debugElement.query(By.css('#runHunt'));
       button.triggerEventHandler('click', new MouseEvent('click'));

       fixture.detectChanges();
       expect(newHuntLocalStore.runHunt).toHaveBeenCalled();

       newHuntLocalStore.mockedObservables.huntId$.next('h1234');
       fixture.detectChanges();

       expect(newHuntLocalStore.requestHuntApproval)
           .toHaveBeenCalledWith('h1234', {
             notifiedUsers: ['user@gmail.com'],
             reason: 'sample reason',
             emailCcAddresses: ['foo@example.org'],
           });
     });

  it('changes the route when finishes sending request', fakeAsync(() => {
       const fixture = TestBed.createComponent(NewHunt);
       fixture.detectChanges();
       const newHuntLocalStore =
           injectMockStore(NewHuntLocalStore, fixture.debugElement);
       fixture.detectChanges();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: true,
       });

       newHuntLocalStore.mockedObservables.huntId$.next('h1234');
       fixture.detectChanges();
       newHuntLocalStore.mockedObservables.huntRequestStatus$.next(
           {status: RequestStatusType.SENT});
       fixture.detectChanges();
       tick();

       const location = TestBed.inject(Location);
       expect(location.path()).toEqual('/hunts/h1234');
     }));

  it('changes the route when finishes sending request when hunt approval is not required',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(NewHunt);
       fixture.detectChanges();
       const newHuntLocalStore =
           injectMockStore(NewHuntLocalStore, fixture.debugElement);
       fixture.detectChanges();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: false,
       });

       newHuntLocalStore.mockedObservables.huntId$.next('h1234');
       fixture.detectChanges();
       tick();

       const location = TestBed.inject(Location);
       expect(location.path()).toEqual('/hunts/h1234');
     }));

  it('does not show approval form when is not needed', fakeAsync(() => {
       const fixture = TestBed.createComponent(NewHunt);
       fixture.detectChanges();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: false,
       });
       fixture.detectChanges();

       expect(fixture.componentInstance.approval).toBe(undefined);
     }));
});
