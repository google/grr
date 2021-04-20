import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, RouterLink} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {Client} from '@app/lib/models/client';
import {ClientSearchFacade} from '@app/store/client_search_facade';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {newClient} from '../../lib/models/model_test_util';

import {ClientSearch} from './client_search';
import {ClientSearchModule} from './module';




initTestEnvironment();

function htmlCollectionToList(c: HTMLCollection): Element[] {
  const result: Element[] = [];
  for (let i = 0; i < c.length; ++i) {
    const item = c.item(i);
    if (item) {
      result.push(item);
    }
  }

  return result;
}

describe('ClientSearch Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let facade: ClientSearchFacade;

  beforeEach(waitForAsync(() => {
    paramsSubject = new Subject();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,  // This makes test faster and more stable.
            ApiModule,
            ClientSearchModule,
            RouterTestingModule,
          ],
          providers: [{
            provide: ActivatedRoute,
            useValue: {
              queryParamMap: paramsSubject,
            },
          }],

        })
        .compileComponents();

    facade = TestBed.inject(ClientSearchFacade);
  }));

  it('triggers a new search on route change', () => {
    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    const searchClientsSpy = spyOn(facade, 'searchClients');
    paramsSubject.next(new Map([
      ['q', 'foo'],
    ]));
    fixture.detectChanges();

    expect(searchClientsSpy).toHaveBeenCalledWith('foo');
  });

  it('displays a list of clients on clients change', () => {
    const subject = new Subject<Client[]>();
    Object.defineProperty(facade, 'clients$', {
      get() {
        return subject.asObservable();
      }
    });

    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    // Simulate initial emission on subscription.
    subject.next([]);

    subject.next([
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'foo.unknown',
        },
        lastSeenAt: new Date(1571789996678),
      }),
      newClient({
        clientId: 'C.5678',
        knowledgeBase: {
          fqdn: 'bar.unknown',
        },
      }),
    ]);
    fixture.detectChanges();

    // Using nativeElement here instead of queryAll, since queryAll does
    // not go into child components DOM (in this case we're interested in
    // what's inside MatTable).
    const de: HTMLElement = fixture.debugElement.nativeElement;
    const rows = de.getElementsByTagName('tr');
    // First row is the header, two others are data.
    expect(rows.length).toBe(3);
    // Check the first data row.
    expect(htmlCollectionToList(rows[1].getElementsByTagName('td'))
               .map((e: Element) => (e as HTMLElement).innerText))
        .toEqual(['C.1234', 'foo.unknown', '2019-10-23 00:19:56 UTC']);
    expect(rows[1].hasAttribute('ng-reflect-query-params')).toBeFalse();
    // Check the second data row.
    expect(htmlCollectionToList(rows[2].getElementsByTagName('td'))
               .map((e: Element) => (e as HTMLElement).innerText))
        .toEqual(['C.5678', 'bar.unknown', 'Unknown']);
    expect(rows[2].hasAttribute('ng-reflect-query-params')).toBeFalse();
  });

  it('includes the reason url param in client urls', () => {
    const subject = new Subject<Client[]>();
    Object.defineProperty(facade, 'clients$', {
      get() {
        return subject.asObservable();
      }
    });

    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    // Simulate initial emission on subscription.
    subject.next([]);

    subject.next([
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'foo.unknown',
        },
        lastSeenAt: new Date(1571789996678),
      }),
    ]);
    fixture.detectChanges();
    paramsSubject.next(new Map([
      ['reason', 'vimes/t/123'],
    ]));
    fixture.detectChanges();

    // Traverse the levels in the DOM tree manually since we can't use
    // queryAll to query the childComponent here.
    const matTable = fixture.debugElement.children[0];
    const matTableBody = matTable.children[1];
    const dataRow = matTableBody.children[0];
    expect(dataRow.injector.get(RouterLink).queryParams).toEqual({
      reason: 'vimes/t/123'
    });
  });
});
