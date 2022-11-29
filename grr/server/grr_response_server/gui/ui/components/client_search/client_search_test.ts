import {Location} from '@angular/common';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterLink} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiModule} from '../../lib/api/module';
import {newClient} from '../../lib/models/model_test_util';
import {ClientSearchLocalStore} from '../../store/client_search_local_store';
import {ClientSearchLocalStoreMock, mockClientSearchLocalStore} from '../../store/client_search_local_store_test_util';
import {STORE_PROVIDERS} from '../../store/store_test_providers';
import {initTestEnvironment} from '../../testing';

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
  let store: ClientSearchLocalStoreMock;

  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ApiModule,
            ClientSearchModule,
            RouterTestingModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
            {
              provide: ClientSearchLocalStore,
              useFactory: () => store,
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    store = mockClientSearchLocalStore();
  }));

  it('triggers a new search on route change', async () => {
    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    await TestBed.inject(Router).navigate([], {queryParams: {q: 'foo'}});
    fixture.detectChanges();

    expect(store.searchClients).toHaveBeenCalledWith('foo');
  });

  it('displays a list of clients on clients change', () => {
    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    // Simulate initial emission on subscription.
    store.mockedObservables.clients$.next([]);

    store.mockedObservables.clients$.next([
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'foo.unknown',
          users: [{username: 'foouser'}, {username: 'admin'}],
        },
        lastSeenAt: new Date(1571789996678),
      }),
      newClient({
        clientId: 'C.5678',
        knowledgeBase: {
          fqdn: 'bar.unknown',
          users: [{username: 'baruser'}],
        },
        labels: [
          {name: 'barlabel', owner: ''},
        ],
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
        .toEqual([
          'C.1234',
          'foo.unknown',
          'foouser + 1',
          '',
          jasmine.stringMatching('Offline'),
          jasmine.stringMatching('2019-10-23 00:19:56 UTC'),
        ]);
    expect(rows[1].hasAttribute('ng-reflect-query-params')).toBeFalse();
    // Check the second data row.
    expect(htmlCollectionToList(rows[2].getElementsByTagName('td'))
               .map((e: Element) => (e as HTMLElement).innerText))
        .toEqual([
          'C.5678',
          'bar.unknown',
          'baruser',
          'barlabel',
          '',
          '',
        ]);
    expect(rows[2].hasAttribute('ng-reflect-query-params')).toBeFalse();
  });

  it('includes the reason url param in client urls', async () => {
    const fixture = TestBed.createComponent(ClientSearch);
    // Ensure ngOnInit hook completes.
    fixture.detectChanges();

    // Simulate initial emission on subscription.
    store.mockedObservables.clients$.next([]);

    store.mockedObservables.clients$.next([
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'foo.unknown',
        },
        lastSeenAt: new Date(1571789996678),
      }),
    ]);
    fixture.detectChanges();
    await TestBed.inject(Router).navigate(
        [], {queryParams: {reason: 'foo/t/123'}});

    fixture.detectChanges();

    // Traverse the levels in the DOM tree manually since we can't use
    // queryAll to query the childComponent here.
    const matTable = fixture.debugElement.query(By.css('table'));
    const matTableBody = matTable.children[1];
    const dataRow = matTableBody.children[0];
    expect(dataRow.injector.get(RouterLink).queryParams).toEqual({
      reason: 'foo/t/123'
    });
  });

  it('changes the route when query is submitted', fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientSearch);
       const componentInstance = fixture.componentInstance;
       componentInstance.onQuerySubmitted('foo');
       tick();

       const location = TestBed.inject(Location);
       expect(location.path()).toEqual('/clients?q=foo');
     }));

  it('preserves reason in the route when a new query is submitted',
     fakeAsync(async () => {
       await TestBed.inject(Router).navigate(
           [], {queryParams: {'q': 'foo', 'reason': 'testreason'}});

       const fixture = TestBed.createComponent(ClientSearch);
       const componentInstance = fixture.componentInstance;
       await componentInstance.onQuerySubmitted('bar');
       tick();

       const location = TestBed.inject(Location);
       expect(location.path()).toEqual('/clients?q=bar&reason=testreason');
     }));
});
