import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterLink} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';
import {initTestEnvironment} from '@app/testing';

import {newClient} from '../../lib/models/model_test_util';
import {ClientSearchGlobalStore} from '../../store/client_search_global_store';
import {ClientSearchGlobalStoreMock, mockClientSearchGlobalStore} from '../../store/client_search_global_store_test_util';

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
  let store: ClientSearchGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,  // This makes test faster and more stable.
            ApiModule,
            ClientSearchModule,
            RouterTestingModule,
          ],
          providers: [
            {
              provide: ClientSearchGlobalStore,
              useFactory: () => store,
            },
          ],

        })
        .compileComponents();

    store = mockClientSearchGlobalStore();
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
    const matTable = fixture.debugElement.children[0];
    const matTableBody = matTable.children[1];
    const dataRow = matTableBody.children[0];
    expect(dataRow.injector.get(RouterLink).queryParams).toEqual({
      reason: 'foo/t/123'
    });
  });
});
