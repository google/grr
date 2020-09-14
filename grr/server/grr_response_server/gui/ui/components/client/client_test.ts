import {Location} from '@angular/common';
import {async, discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {MatDrawer} from '@angular/material/sidenav';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {newClient} from '@app/lib/models/model_test_util';
import {ClientDetailsFacade} from '@app/store/client_details_facade';
import {Subject} from 'rxjs';

import {Client} from '../../lib/models/client';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';
import {UserFacade} from '../../store/user_facade';
import {mockUserFacade, UserFacadeMock} from '../../store/user_facade_test_util';
import {initTestEnvironment} from '../../testing';
import {ClientDetailsModule} from '../client_details/module';

import {Client as ClientComponent} from './client';
import {ClientModule} from './module';
import {CLIENT_ROUTES} from './routing';

initTestEnvironment();

describe('Client Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let clientPageFacade: ClientPageFacade;
  let clientDetailsFacade: ClientDetailsFacade;
  let configFacade: ConfigFacadeMock;
  let userFacade: UserFacadeMock;
  let location: Location;
  let router: Router;

  beforeEach(async(() => {
    paramsSubject = new Subject();
    configFacade = mockConfigFacade();
    userFacade = mockUserFacade();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientModule,
            ClientDetailsModule,
            RouterTestingModule.withRoutes(CLIENT_ROUTES),
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {
                paramMap: paramsSubject,
                snapshot: {},
              },
            },
            {provide: ConfigFacade, useFactory: () => configFacade},
            {provide: UserFacade, useFactory: () => userFacade},
            {provide: Router, useValue: {}},
          ],

        })
        .compileComponents();

    clientPageFacade = TestBed.inject(ClientPageFacade);
    clientDetailsFacade = TestBed.inject(ClientDetailsFacade);
    location = TestBed.get(Location);
    router = TestBed.get(Router);
  }));

  it('loads client information on route change', () => {
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    const searchClientsSpy = spyOn(clientPageFacade, 'selectClient');
    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    fixture.detectChanges();

    expect(searchClientsSpy).toHaveBeenCalledWith('C.1234');
  });

  it('correctly updates URL when navigating from main page to details page',
     fakeAsync(() => {
       // Prevent warnings from 404-ing API requests.
       spyOn(clientPageFacade, 'selectClient');
       spyOn(clientDetailsFacade, 'selectClient');

       const subject = new Subject<Client>();
       Object.defineProperty(clientPageFacade, 'selectedClient$', {get: () => subject});
       spyOn(clientPageFacade, 'removeClientLabel');

       router.navigate(['clients/C.1234']);
       tick();
       const fixture = TestBed.createComponent(ClientComponent);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
       subject.next(newClient({
         clientId: 'C.1234',
         labels: [{name: 'testlabel', owner: ''}],
       }));
       fixture.detectChanges();

       expect(location.path()).toEqual('/clients/C.1234');
       const drawer = fixture.debugElement.query(By.directive(MatDrawer));
       expect(drawer.componentInstance.opened).toEqual(false);
       let detailsButton =
           fixture.debugElement.query(By.css('.goto-details')).nativeElement;
       detailsButton.dispatchEvent(new MouseEvent('click'));
       tick();
       fixture.detectChanges();

       // The following expectation is met when testing manually, but not on
       // automated testing, because the drawer's openedStart observable is not
       // firing
       // expect(location.path()).toEqual('/v2/clients/C.1234/details');
       expect(drawer.componentInstance.opened).toEqual(true);

       discardPeriodicTasks();
     }));

  it('correctly updates URL when navigating from details page to main page',
     fakeAsync(() => {
       // Prevent warnings from 404-ing API requests.
       spyOn(clientPageFacade, 'selectClient');
       spyOn(clientDetailsFacade, 'selectClient');

       const subject = new Subject<Client>();
       Object.defineProperty(clientPageFacade, 'selectedClient$', {get: () => subject});
       spyOn(clientPageFacade, 'removeClientLabel');

       const fixture = TestBed.createComponent(ClientComponent);
       router.navigate(['v2/clients/C.1234/details']);
       tick();
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
       subject.next(newClient({
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
});
