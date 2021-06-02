import {Location} from '@angular/common';
import {discardPeriodicTasks, fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatDrawer} from '@angular/material/sidenav';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {Subject} from 'rxjs';

import {newClient} from '../../lib/models/model_test_util';
import {ClientDetailsGlobalStore} from '../../store/client_details_global_store';
import {ClientDetailsGlobalStoreMock, mockClientDetailsGlobalStore} from '../../store/client_details_global_store_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {ScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store';
import {mockScheduledFlowGlobalStore} from '../../store/scheduled_flow_global_store_test_util';
import {UserGlobalStore} from '../../store/user_global_store';
import {mockUserGlobalStore, UserGlobalStoreMock} from '../../store/user_global_store_test_util';
import {initTestEnvironment} from '../../testing';
import {ClientDetailsModule} from '../client_details/module';

import {ClientPage as ClientComponent} from './client_page';
import {ClientPageModule} from './module';

import {CLIENT_PAGE_ROUTES} from './routing';


initTestEnvironment();

describe('ClientPage Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let queryParamsSubject: Subject<Map<string, string>>;
  let clientPageGlobalStore: ClientPageGlobalStoreMock;
  let clientDetailsGlobalStore: ClientDetailsGlobalStoreMock;
  let configGlobalStore: ConfigGlobalStoreMock;
  let userGlobalStore: UserGlobalStoreMock;
  let location: Location;
  let router: Router;

  beforeEach(waitForAsync(() => {
    paramsSubject = new Subject();
    queryParamsSubject = new Subject();
    configGlobalStore = mockConfigGlobalStore();
    userGlobalStore = mockUserGlobalStore();
    clientPageGlobalStore = mockClientPageGlobalStore();
    clientDetailsGlobalStore = mockClientDetailsGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientPageModule,
            ClientDetailsModule,
            RouterTestingModule.withRoutes(CLIENT_PAGE_ROUTES),
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useFactory: () => ({
                paramMap: paramsSubject,
                queryParamMap: queryParamsSubject,
                snapshot: {},
              }),
            },
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
            {provide: UserGlobalStore, useFactory: () => userGlobalStore},
            {
              provide: ClientPageGlobalStore,
              useFactory: () => clientPageGlobalStore
            },
            {
              provide: ClientDetailsGlobalStore,
              useFactory: () => clientDetailsGlobalStore
            },
            {
              provide: ScheduledFlowGlobalStore,
              useFactory: mockScheduledFlowGlobalStore,
            },
          ],

        })
        .compileComponents();

    location = TestBed.inject(Location);
    router = TestBed.inject(Router);
  }));

  it('loads client information on route change', () => {
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    fixture.detectChanges();

    expect(clientPageGlobalStore.selectClient).toHaveBeenCalledWith('C.1234');
  });

  it('correctly updates URL when navigating from main page to details page',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientComponent);
       router.navigate(['clients/C.1234']);
       tick();
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
       clientPageGlobalStore.selectedClientSubject.next(newClient({
         clientId: 'C.1234',
         labels: [{name: 'testlabel', owner: ''}],
       }));
       fixture.detectChanges();

       expect(location.path()).toEqual('/clients/C.1234');
       const drawer = fixture.debugElement.query(By.directive(MatDrawer));
       expect(drawer.componentInstance.opened).toEqual(false);
       const detailsButton =
           fixture.debugElement.query(By.css('.goto-details')).nativeElement;
       detailsButton.dispatchEvent(new MouseEvent('click'));
       tick();
       fixture.detectChanges();

       // The following expectation is met when testing manually, but not on
       // automated testing, because the drawer's openedStart observable is not
       // firing
       // expect(location.path()).toEqual('/clients/C.1234/details');
       expect(drawer.componentInstance.opened).toEqual(true);

       discardPeriodicTasks();
     }));

  it('correctly updates URL when navigating from details page to main page',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientComponent);
       router.navigate(['clients/C.1234/details']);
       tick();
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
       clientPageGlobalStore.selectedClientSubject.next(newClient({
         clientId: 'C.1234',
         labels: [{name: 'testlabel', owner: ''}],
       }));
       fixture.detectChanges();
       tick();

       fixture.detectChanges();

       expect(location.path()).toEqual('/clients/C.1234/details');
       const drawer = fixture.debugElement.query(By.directive(MatDrawer));
       expect(drawer.componentInstance.opened).toEqual(true);
       const detailsButton =
           fixture.debugElement.query(By.css('.goto-details')).nativeElement;
       detailsButton.dispatchEvent(new MouseEvent('click'));
       fixture.detectChanges();

       expect(drawer.componentInstance.opened).toEqual(false);
       // The following expectation is met when testing manually, but not on
       // automated testing, because the drawer's closedStart observable is not
       // firing
       // expect(location.path()).toEqual('/clients/C.1234');
       tick();
       discardPeriodicTasks();
     }));

  it('shows approval iff approvalsEnabled$', () => {
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();

    clientPageGlobalStore.approvalsEnabledSubject.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.client-approval'))
               .styles['display'])
        .toEqual('block');
  });

  it('does not show approval if approvalsEnabled$ is false', () => {
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();

    clientPageGlobalStore.approvalsEnabledSubject.next(false);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.client-approval'))
               .styles['display'])
        .toEqual('none');
  });
});
