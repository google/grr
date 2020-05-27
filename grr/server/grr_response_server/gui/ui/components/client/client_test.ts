import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {Subject} from 'rxjs';

import {Client} from '../../lib/models/client';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';
import {GrrStoreModule} from '../../store/store_module';
import {initTestEnvironment} from '../../testing';

import {Client as ClientComponent} from './client';
import {ClientModule} from './module';



initTestEnvironment();

describe('Client Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let facade: ClientPageFacade;
  let configFacade: ConfigFacadeMock;

  beforeEach(async(() => {
    paramsSubject = new Subject();
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            ClientModule,
            GrrStoreModule,
            NoopAnimationsModule,
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {
                paramMap: paramsSubject,
              },
            },
            {provide: ConfigFacade, useFactory: () => configFacade},
          ],

        })
        .compileComponents();

    facade = TestBed.inject(ClientPageFacade);
  }));

  it('loads client information on route change', () => {
    const fixture = TestBed.createComponent(ClientComponent);
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

    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    subject.next({
      clientId: 'C.1234',
      fleetspeakEnabled: true,
      knowledgeBase: {
        fqdn: 'foo.unknown',
      },
      lastSeenAt: new Date(1571789996678),
      labels: [],
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1234');
    expect(text).toContain('foo.unknown');
  });
});
