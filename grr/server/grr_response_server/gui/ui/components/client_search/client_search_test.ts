import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_test_util';
import {newClient, newClientApproval} from '../../lib/models/model_test_util';
import {ClientSearchStore} from '../../store/client_search_store';
import {
  ClientSearchStoreMock,
  newClientSearchStoreMock,
} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {CLIENT_ROUTES} from '../app/routing';
import {ClientSearch} from './client_search';
import {ClientSearchHarness} from './testing/client_search_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientSearch);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientSearchHarness,
  );

  return {fixture, harness};
}

describe('Client Search Component', () => {
  let clientSearchStoreMock: ClientSearchStoreMock;

  beforeEach(waitForAsync(() => {
    clientSearchStoreMock = newClientSearchStoreMock();

    TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        ClientSearch,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    })
      .overrideComponent(ClientSearch, {
        set: {
          providers: [
            {
              provide: ClientSearchStore,
              useValue: clientSearchStoreMock,
            },
          ],
        },
      })
      .compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('calls store to fetch recent clients', fakeAsync(async () => {
    await createComponent();

    expect(
      clientSearchStoreMock.fetchRecentClientApprovals,
    ).toHaveBeenCalledTimes(1);
  }));

  it('displays the list of clients from the store', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
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
          {name: 'barlabel2', owner: 'baruser'},
        ],
      }),
    ]);
    const {harness} = await createComponent();

    const rows = await harness.getRows();
    expect(rows.length).toBe(2);
    expect(await harness.getCellText(0, 'fqdn')).toBe('foo.unknown');
    expect(await harness.getCellText(0, 'users')).toBe('foouser + 1');
    expect(await harness.getCellText(0, 'online')).toContain('Offline');
    expect(await harness.getCellText(0, 'lastSeenAt')).toContain(
      '2019-10-23 00:19:56 UTC',
    );
    expect(await harness.getCellText(1, 'fqdn')).toBe('bar.unknown');
    expect(await harness.getCellText(1, 'users')).toBe('baruser');
    expect(await harness.getCellText(1, 'labels')).toContain('barlabel');
    expect(await harness.getCellText(1, 'labels')).toContain('barlabel2');
    expect(await harness.getCellText(1, 'online')).toBe('');
    expect(await harness.getCellText(1, 'lastSeenAt')).toBe('');
  }));

  it('can sort by client id', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
      }),
      newClient({
        clientId: 'C.5678',
      }),
    ]);
    const {harness} = await createComponent();

    const sort = await harness.getTableSort();
    const clientIdHeader = await sort.getSortHeaders({label: 'Client ID'});
    await clientIdHeader[0].click();

    expect(await clientIdHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
    expect(await harness.getCellText(1, 'clientId')).toContain('C.5678');
  }));

  it('can sort by fqdn', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'b.unknown',
        },
      }),
      newClient({
        clientId: 'C.5678',
        knowledgeBase: {
          fqdn: 'a.unknown',
        },
      }),
    ]);
    const {harness} = await createComponent();

    const sort = await harness.getTableSort();
    const fqdnHeader = await sort.getSortHeaders({label: 'FQDN'});
    await fqdnHeader[0].click();

    expect(await fqdnHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'fqdn')).toBe('a.unknown');
    expect(await harness.getCellText(1, 'fqdn')).toBe('b.unknown');
  }));

  it('can sort by last seen at', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
        lastSeenAt: new Date(111111),
      }),
      newClient({
        clientId: 'C.2345',
        lastSeenAt: new Date(333333),
      }),
      newClient({
        clientId: 'C.3456',
        lastSeenAt: new Date(222222),
      }),
    ]);
    const {harness} = await createComponent();

    const sort = await harness.getTableSort();
    const lastSeenAtHeader = await sort.getSortHeaders({label: 'Last seen'});
    await lastSeenAtHeader[0].click();

    expect(await lastSeenAtHeader[0].getSortDirection()).toBe('asc');
    expect(await harness.getRows()).toHaveSize(3);
    expect(await harness.getCellText(0, 'lastSeenAt')).toContain(
      '1970-01-01 00:01:51 UTC',
    );
    expect(await harness.getCellText(1, 'lastSeenAt')).toContain(
      '1970-01-01 00:03:42 UTC',
    );
    expect(await harness.getCellText(2, 'lastSeenAt')).toContain(
      '1970-01-01 00:05:33 UTC',
    );
  }));

  it('can filter by client id', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
      }),
      newClient({
        clientId: 'C.5678',
      }),
    ]);
    const {harness, fixture} = await createComponent();

    fixture.componentInstance.dataSource.filter = 'C.1234';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));

  it('can filter by fqdn', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'b.fqdn',
        },
      }),
      newClient({
        clientId: 'C.5678',
        knowledgeBase: {
          fqdn: 'a.fqdn',
        },
      }),
    ]);
    const {harness, fixture} = await createComponent();

    fixture.componentInstance.dataSource.filter = 'a.fqdn';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'fqdn')).toBe('a.fqdn');
    expect(await harness.getCellText(0, 'clientId')).toContain('C.5678');
  }));

  it('can filter by users', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          users: [{username: 'foouser'}, {username: 'admin'}],
        },
      }),
      newClient({
        clientId: 'C.5678',
        knowledgeBase: {
          users: [{username: 'baruser'}],
        },
      }),
    ]);
    const {harness, fixture} = await createComponent();

    fixture.componentInstance.dataSource.filter = 'baruser';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'users')).toBe('baruser');
    expect(await harness.getCellText(0, 'clientId')).toContain('C.5678');
  }));

  it('can filter by labels', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
        labels: [
          {name: 'barlabel', owner: ''},
          {name: 'barlabel2', owner: 'baruser'},
        ],
      }),
      newClient({
        clientId: 'C.5678',
        labels: [{name: 'foolabel', owner: ''}],
      }),
    ]);
    const {harness, fixture} = await createComponent();

    fixture.componentInstance.dataSource.filter = 'barlabel';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'labels')).toContain('barlabel');
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));

  it('can filter by last seen at by milliseconds since epoch', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
        lastSeenAt: new Date(111111), // 1970-01-01 00:01:51 UTC
      }),
      newClient({
        clientId: 'C.5678',
        lastSeenAt: new Date(222222), // 1970-01-01 00:03:42 UTC
      }),
    ]);
    const {harness, fixture} = await createComponent();

    fixture.componentInstance.dataSource.filter = '111111';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'lastSeenAt')).toContain(
      '1970-01-01 00:01:51 UTC',
    );
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));

  it('can filter by last seen at by UTC string date', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
        lastSeenAt: new Date(111111), // 1970-01-01 00:01:51 UTC
      }),
      newClient({
        clientId: 'C.5678',
        lastSeenAt: new Date(222222), // 1970-01-01 00:03:42 UTC
      }),
    ]);
    const {harness, fixture} = await createComponent();

    fixture.componentInstance.dataSource.filter = '1 Jan 1970 00:01:51';

    expect(await harness.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'lastSeenAt')).toContain(
      '1970-01-01 00:01:51 UTC',
    );
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));

  it('shows no results message in search table when there are no results', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([]);
    const {harness} = await createComponent();

    const table = await harness.table();
    expect(await (await table.host()).text()).toContain(
      'No search results found.',
    );
  }));

  it('displays recent approvals', fakeAsync(async () => {
    clientSearchStoreMock.recentApprovals = signal([
      newClientApproval({}),
      newClientApproval({}),
    ]);
    const {harness} = await createComponent();

    expect(await harness.recentApprovals()).toHaveSize(2);
  }));

  it('links to the client flows list when the approval reason is not set', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
      }),
    ]);
    await TestBed.inject(Router).navigate([], {
      queryParams: {},
    });
    const {harness} = await createComponent();

    // The fqdn cell has no copy-button, so the click should open the client
    // page.
    const fqdnCell = await harness.getCell(0, 'fqdn');
    await (await fqdnCell.host()).click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual('/clients/C.1234/flows');
  }));

  it('links to the client approvals when the approval reason is set and keeps the reason in the URL', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({
        clientId: 'C.1234',
      }),
    ]);
    await TestBed.inject(Router).navigate([], {
      queryParams: {'reason': 'testreason'},
    });
    const {harness} = await createComponent();

    // The fqdn cell has no copy-button, so the click should open the client
    // page.
    const fqdnCell = await harness.getCell(0, 'fqdn');
    await (await fqdnCell.host()).click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual(
      '/clients/C.1234/approvals?reason=testreason',
    );
  }));
});
