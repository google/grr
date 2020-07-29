import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {ApiModule} from '@app/lib/api/module';
import {Client} from '@app/lib/models/client';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {ConfigFacade} from '@app/store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '@app/store/config_facade_test_util';
import {Subject} from 'rxjs';

import {initTestEnvironment} from '../../testing';

import {ClientDetails} from './client_details';
import {ClientDetailsModule} from './module';

initTestEnvironment();

describe('Client Details Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let facade: ClientPageFacade;
  let configFacade: ConfigFacadeMock;

  beforeEach(async(() => {
    paramsSubject = new Subject();
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientDetailsModule,
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {
                paramMap: paramsSubject,
              },
            },
            {provide: ConfigFacade, useFactory: () => configFacade},
            {provide: Router, useValue: {}},
          ],

        })
        .compileComponents();

    facade = TestBed.inject(ClientPageFacade);
  }));

  it('loads client information on route change', () => {
    const fixture = TestBed.createComponent(ClientDetails);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    const searchClientsSpy = spyOn(facade, 'selectClient');
    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    fixture.detectChanges();

    expect(searchClientsSpy).toHaveBeenCalledWith('C.1234');
  });

  it('displays client details on client change', () => {
    // Prevent warnings from 404-ing API requests.
    spyOn(facade, 'selectClient');

    const subject = new Subject<Client>();
    Object.defineProperty(facade, 'selectedClient$', {get: () => subject});

    const fixture = TestBed.createComponent(ClientDetails);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    subject.next({
      clientId: 'C.1234',
      fleetspeakEnabled: true,
      knowledgeBase: {
        fqdn: 'foo.unknown',
      },
      agentInfo: {},
      osInfo: {},
      users: [],
      networkInterfaces: [],
      volumes: [],
      lastSeenAt: new Date(1571789996678),
      labels: [],
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1234');
    expect(text).toContain('foo.unknown');
  });
});
