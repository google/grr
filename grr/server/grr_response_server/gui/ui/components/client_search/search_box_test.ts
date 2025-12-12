import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterModule} from '@angular/router';

import {newClient} from '../../lib/models/model_test_util';
import {ClientSearchStore} from '../../store/client_search_store';
import {GlobalStore} from '../../store/global_store';
import {
  ClientSearchStoreMock,
  GlobalStoreMock,
  newClientSearchStoreMock,
  newGlobalStoreMock,
} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {CLIENT_ROUTES} from '../app/routing';
import {SearchBox} from './search_box';
import {SearchBoxHarness} from './testing/search_box_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(SearchBox);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    SearchBoxHarness,
  );

  return {fixture, harness};
}

describe('Search Box', () => {
  let clientSearchStoreMock: ClientSearchStoreMock;
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    clientSearchStoreMock = newClientSearchStoreMock();
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [
        SearchBox,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: ClientSearchStore,
          useValue: clientSearchStoreMock,
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('creates the component', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('updates the query on route change', async () => {
    const {fixture} = await createComponent();

    await TestBed.inject(Router).navigate([], {queryParams: {'q': 'foo'}});
    fixture.detectChanges();

    expect(fixture.componentInstance.searchFormControl.value).toEqual('foo');
  });

  it('calls store to search clients', fakeAsync(async () => {
    await createComponent();

    expect(clientSearchStoreMock.searchClients).toHaveBeenCalledTimes(1);
  }));

  it('calls Store to search clients when enter is pressed', fakeAsync(async () => {
    const {harness} = await createComponent();

    const searchInput = await harness.searchInput();
    await searchInput.setValue('foo');
    await harness.sendEnterKey();

    // First call is made when the component is created with the query as
    // signal. Seconds call is made when enter is pressed with the query from
    // the input.
    expect(clientSearchStoreMock.searchClients).toHaveBeenCalledTimes(2);
    const calls = // tslint:disable-next-line:no-any
      (clientSearchStoreMock.searchClients! as any as jasmine.Spy).calls.all();
    expect(calls[1].args[0]).toEqual('foo');
  }));

  it('does not call store to search clients on enter when query is empty', async () => {
    const {harness} = await createComponent();

    const searchInput = await harness.searchInput();
    await searchInput.setValue('');
    await harness.sendEnterKey();

    // First call is made when the component is created with the query as
    // signal.
    expect(clientSearchStoreMock.searchClients).toHaveBeenCalledTimes(1);
  });

  it('does not call store to search clients on enter when query is whitespace', async () => {
    const {harness} = await createComponent();

    const searchInput = await harness.searchInput();
    await searchInput.setValue('   ');
    await harness.sendEnterKey();

    // First call is made when the component is created with the query as
    // signal.
    expect(clientSearchStoreMock.searchClients).toHaveBeenCalledTimes(1);
  });

  it('shows autocomplete options provided by the store', fakeAsync(async () => {
    clientSearchStoreMock.clients = signal([
      newClient({clientId: 'C.1234567890'}),
      newClient({clientId: 'C.1234567891'}),
      newClient({clientId: 'C.1234567892'}),
    ]);
    const {harness} = await createComponent();

    const autocomplete = await harness.autocomplete();
    const options = await autocomplete.getOptions();
    expect(options.length).toBe(3);
    expect(await options[0].getText()).toContain('C.1234567890');
    expect(await options[1].getText()).toContain('C.1234567891');
    expect(await options[2].getText()).toContain('C.1234567892');
  }));

  it('shows labels in autocomplete options when input starts with `label:`', async () => {
    globalStoreMock.allLabels = signal(['test1', 'test2', 'other']);
    const {harness} = await createComponent();

    const searchInput = await harness.searchInput();
    await searchInput.setValue('label:test');

    const autocomplete = await harness.autocomplete();
    const options = await autocomplete.getOptions();
    expect(options.length).toBe(2);
    expect(await options[0].getText()).toContain('test1');
    expect(await options[1].getText()).toContain('test2');
  });

  it('excludes labels in autocomplete options when input does not start with `label:`', async () => {
    globalStoreMock.allLabels = signal(['test1', 'test2', 'other']);
    const {harness} = await createComponent();

    const searchInput = await harness.searchInput();
    await searchInput.setValue('test');

    const autocomplete = await harness.autocomplete();
    expect(await autocomplete.isOpen()).toBeFalse();
  });

  it('trims whitespace from label query', async () => {
    globalStoreMock.allLabels = signal(['test1', 'test2', 'other']);
    const {harness} = await createComponent();

    const searchInput = await harness.searchInput();
    await searchInput.setValue('label:  test  ');

    const autocomplete = await harness.autocomplete();
    const options = await autocomplete.getOptions();
    expect(options.length).toBe(2);
    expect(await options[0].getText()).toContain('test1');
    expect(await options[1].getText()).toContain('test2');
  });

  it('changes the route when query is submitted', async () => {
    await TestBed.inject(Router).navigate([], {
      queryParams: {'q': 'foo'},
    });
    const {harness} = await createComponent();

    const searchInput = await harness.searchInput();
    await searchInput.setValue('bar');
    await harness.sendEnterKey();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual('/clients?q=bar');
  });

  it('preserves `reason` query param in the route when a new query is submitted', fakeAsync(async () => {
    await TestBed.inject(Router).navigate([], {
      queryParams: {'q': 'foo', 'reason': 'testreason'},
    });

    const {harness} = await createComponent();
    const searchInput = await harness.searchInput();
    await searchInput.setValue('bar');
    await harness.sendEnterKey();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual('/clients?q=bar&reason=testreason');
  }));

  it('navigates to the client flows when a client ID is selected and no `reason` query param is set', fakeAsync(async () => {
    await TestBed.inject(Router).navigate([], {
      queryParams: {'q': 'C.1234567890abcdef'},
    });
    clientSearchStoreMock.clients = signal([
      newClient({clientId: 'C.1234567890abcdef'}),
    ]);
    const {harness} = await createComponent();

    const autocomplete = await harness.autocomplete();
    const options = await autocomplete.getOptions();
    await options[0].click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual('/clients/C.1234567890abcdef/flows');
  }));

  it('navigates to the client approvals when a client ID is selected and a `reason` query param is set', fakeAsync(async () => {
    await TestBed.inject(Router).navigate([], {
      queryParams: {'q': 'C.1234567890abcdef', 'reason': 'testreason'},
    });
    clientSearchStoreMock.clients = signal([
      newClient({clientId: 'C.1234567890abcdef'}),
    ]);
    const {harness} = await createComponent();

    const autocomplete = await harness.autocomplete();
    const options = await autocomplete.getOptions();
    await options[0].click();
    tick();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual(
      '/clients/C.1234567890abcdef/approvals?reason=testreason',
    );
  }));
});
