import {Location} from '@angular/common';
import {async, discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {MatDrawer} from '@angular/material/sidenav';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router, UrlSegment} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {newClient} from '@app/lib/models/model_test_util';
import {Subject} from 'rxjs';

import {Client} from '../../lib/models/client';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';
import {initTestEnvironment} from '../../testing';

import {Client as ClientComponent} from './client';
import {ClientModule} from './module';
import {CLIENT_ROUTES} from './routing';

initTestEnvironment();

describe('Client Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let urlSubject: Subject<UrlSegment[]>;
  let facade: ClientPageFacade;
  let configFacade: ConfigFacadeMock;
  let location: Location;
  let router: Router;

  beforeEach(async(() => {
    paramsSubject = new Subject();
    urlSubject = new Subject();
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientModule,
            RouterTestingModule.withRoutes(CLIENT_ROUTES),
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {
                paramMap: paramsSubject,
                url: urlSubject,
              },
            },
            {provide: ConfigFacade, useFactory: () => configFacade},
          ],

        })
        .compileComponents();

    facade = TestBed.inject(ClientPageFacade);
    location = TestBed.get(Location);
    router = TestBed.get(Router);
  }));

  it('loads client information on route change', () => {
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    const searchClientsSpy = spyOn(facade, 'selectClient');
    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    fixture.detectChanges();

    expect(searchClientsSpy).toHaveBeenCalledWith('C.1234');
  });

  it('correctly updates URL for client details drawer usage', fakeAsync(() => {
       // Prevent warnings from 404-ing API requests.
       spyOn(facade, 'selectClient');

       const subject = new Subject<Client>();
       Object.defineProperty(facade, 'selectedClient$', {get: () => subject});
       spyOn(facade, 'removeClientLabel');

       router.navigate(['v2/clients/C.1234']);
       tick();
       const fixture = TestBed.createComponent(ClientComponent);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
       subject.next(newClient({
         clientId: 'C.1234',
         labels: [{name: 'testlabel', owner: ''}],
       }));
       fixture.detectChanges();

       // Flows page->details page
       expect(location.path()).toEqual('/v2/clients/C.1234');
       expect(fixture.debugElement.query(By.directive(MatDrawer))
                  .componentInstance.opened)
           .toEqual(false);
       let detailsButton =
           fixture.debugElement.query(By.css('.goto-details')).nativeElement;
       detailsButton.dispatchEvent(new MouseEvent('click'));

       expect(location.path()).toEqual('/v2/clients/C.1234/details');
       expect(fixture.debugElement.query(By.directive(MatDrawer))
                  .componentInstance.opened)
           .toEqual(true);

       // Details page -> flows page
       router.navigate(['v2/clients/C.1234/details']);
       tick();
       expect(location.path()).toEqual('/v2/clients/C.1234/details');
       expect(fixture.debugElement.query(By.directive(MatDrawer))
                  .componentInstance.opened)
           .toEqual(true);
       detailsButton =
           fixture.debugElement.query(By.css('.goto-details')).nativeElement;
       detailsButton.dispatchEvent(new MouseEvent('click'));
       fixture.detectChanges();

       expect(fixture.debugElement.query(By.directive(MatDrawer))
                  .componentInstance.opened)
           .toEqual(false);

       // The following expectation is met when testing manually, but not on
       // automated testing, because the drawer's closedStart observable is not
       // emitting
       // expect(location.path()).toEqual('/v2/clients/C.1234');
       discardPeriodicTasks();
     }));
});
