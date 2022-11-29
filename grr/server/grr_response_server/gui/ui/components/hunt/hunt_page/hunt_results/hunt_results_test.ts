import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatTabGroupHarness} from '@angular/material/tabs/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {Any, ApiHuntError, ApiHuntResult} from '../../../../lib/api/api_interfaces';
import {createStatEntry} from '../../../../lib/api/api_test_util';
import {getHuntResultKey} from '../../../../lib/api_translation/hunt';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';
import {HuntPageGlobalStoreMock, mockHuntPageGlobalStore} from '../../../../store/hunt_page_global_store_test_util';
import {STORE_PROVIDERS} from '../../../../store/store_test_providers';
import {initTestEnvironment} from '../../../../testing';

import {HuntResults} from './hunt_results';
import {HuntResultsModule} from './module';

initTestEnvironment();

function receiveResults(
    huntPageGlobalStore: HuntPageGlobalStoreMock,
    res: ReadonlyArray<ApiHuntResult>) {
  const huntId = 'XXX';
  const results: {[key: string]: ApiHuntResult} = {};
  for (const result of res) {
    results[getHuntResultKey(result, huntId)] = result;
  }

  huntPageGlobalStore.mockedObservables.huntResults$.next({
    isLoading: false,
    results,
  });
  huntPageGlobalStore.mockedObservables.selectedHuntId$.next(huntId);
}

describe('HuntResults', () => {
  let huntPageGlobalStore: HuntPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    huntPageGlobalStore = mockHuntPageGlobalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HuntResultsModule,
            RouterTestingModule.withRoutes([
              // Dummy route to stop error when navigating to details.
              {
                outlet: 'drawer',
                path: 'result-details/:id',
                component: HuntResults
              },
            ]),
          ],
          providers: [...STORE_PROVIDERS],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            HuntPageGlobalStore, {useFactory: () => huntPageGlobalStore})
        .compileComponents();
  }));

  it('loads more on constructor and displays title', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();
    expect(huntPageGlobalStore.loadMoreResults).toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Results');
  });

  it('starts with loading spinner', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();
    expect(huntPageGlobalStore.loadMoreResults).toHaveBeenCalled();
    expect(fixture.nativeElement.querySelectorAll('mat-spinner').length)
        .toBe(1);
  });

  it('displays message when no data', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntId$.next('XXX');
    huntPageGlobalStore.mockedObservables.huntResults$.next(
        {isLoading: true, results: {}});
    huntPageGlobalStore.mockedObservables.huntErrors$.next(
        {isLoading: false, hasMore: false, errors: []});
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Nothing to show');
  });

  it('does NOT display message when there is any data', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntId$.next('XXX');
    huntPageGlobalStore.mockedObservables.huntResults$.next(
        {isLoading: false, hasMore: false, results: {'-': {}}});
    huntPageGlobalStore.mockedObservables.huntErrors$.next(
        {isLoading: true, errors: []});
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Nothing to show');

    huntPageGlobalStore.mockedObservables.huntResults$.next(
        {isLoading: true, results: {}});
    huntPageGlobalStore.mockedObservables.huntErrors$.next(
        {isLoading: false, hasMore: false, errors: [{}]});
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Nothing to show');
  });

  it('displays load more RESULTS button when loading', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntId$.next('XXX');
    huntPageGlobalStore.mockedObservables.huntResults$.next(
        {isLoading: true, results: {'-': {}}});
    fixture.detectChanges();
    const button =
        fixture.debugElement.query(By.css('[name=loadMoreResultsButton]'));
    expect(button.nativeElement.querySelectorAll('mat-spinner').length).toBe(1);
    expect(button.nativeElement.textContent).toContain('Loading more results');

    huntPageGlobalStore.mockedObservables.huntResults$.next(
        {isLoading: false, hasMore: true, results: {'-': {}}});
    fixture.detectChanges();
    expect(button.nativeElement.querySelectorAll('mat-icon').length).toBe(1);
    expect(button.nativeElement.textContent).toContain('Load more results');

    huntPageGlobalStore.mockedObservables.huntResults$.next(
        {isLoading: false, hasMore: false, results: {'-': {}}});
    fixture.detectChanges();
    expect(button.nativeElement.getAttribute('disabled')).toEqual('true');
    expect(button.nativeElement.textContent).toContain('Nothing');
  });

  it('displays load more ERRORS button when loading', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntId$.next('XXX');
    huntPageGlobalStore.mockedObservables.huntErrors$.next(
        {isLoading: true, errors: [{}]});
    fixture.detectChanges();
    const button =
        fixture.debugElement.query(By.css('[name=loadMoreErrorsButton]'));
    expect(button.nativeElement.querySelectorAll('mat-spinner').length).toBe(1);
    expect(button.nativeElement.textContent).toContain('Loading more errors');

    huntPageGlobalStore.mockedObservables.huntErrors$.next(
        {isLoading: false, hasMore: true, errors: [{}]});
    fixture.detectChanges();
    expect(button.nativeElement.querySelectorAll('mat-icon').length).toBe(1);
    expect(button.nativeElement.textContent).toContain('Load more errors');

    huntPageGlobalStore.mockedObservables.huntErrors$.next(
        {isLoading: false, hasMore: false, errors: [{}]});
    fixture.detectChanges();
    expect(button.nativeElement.getAttribute('disabled')).toEqual('true');
    expect(button.nativeElement.textContent).toContain('Nothing');
  });

  it('displays hunt RESULTS from store using appropriate components', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: ReadonlyArray<ApiHuntResult> = [
      {clientId: 'C.1234', timestamp: '1234', payloadType: 'foo'},
      {clientId: 'C.5678', timestamp: '5678', payloadType: 'foo'}
    ];
    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(2);

    enum CellIndexOf { CLIENT_ID = 0, TIMESTAMP, PAYLOAD_TYPE, DETAILS_BUTTON }

    let cells = rows[0].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.1234');
    expect(
        cells[CellIndexOf.TIMESTAMP].querySelectorAll('app-timestamp').length)
        .toBe(1);
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim()).toContain('foo');
    expect(cells[CellIndexOf.DETAILS_BUTTON].innerText.trim())
        .toContain('View details');

    cells = rows[1].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.5678');
    expect(
        cells[CellIndexOf.TIMESTAMP].querySelectorAll('app-timestamp').length)
        .toBe(1);
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim()).toContain('foo');
    expect(cells[CellIndexOf.DETAILS_BUTTON].innerText.trim())
        .toContain('View details');
  });

  it('displays hunt ERRORS from store', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: readonly ApiHuntError[] = [
      {clientId: 'C.1234', logMessage: 'fooLog', backtrace: 'fooTrace'},
      {clientId: 'C.5678', logMessage: 'barLog', backtrace: 'barTrace'}
    ];
    huntPageGlobalStore.mockedObservables.huntErrors$.next(
        {isLoading: false, hasMore: true, errors: res});
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(2);

    enum CellIndexOf { CLIENT_ID = 0, TIMESTAMP, LOG_MESSAGE, BACKTRACE }

    let cells = rows[0].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.1234');
    expect(
        cells[CellIndexOf.TIMESTAMP].querySelectorAll('app-timestamp').length)
        .toBe(1);
    expect(cells[CellIndexOf.LOG_MESSAGE].innerText.trim()).toContain('fooLog');
    expect(cells[CellIndexOf.BACKTRACE].innerText.trim()).toContain('fooTrace');

    cells = rows[1].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.5678');
    expect(
        cells[CellIndexOf.TIMESTAMP].querySelectorAll('app-timestamp').length)
        .toBe(1);
    expect(cells[CellIndexOf.LOG_MESSAGE].innerText.trim()).toContain('barLog');
    expect(cells[CellIndexOf.BACKTRACE].innerText.trim()).toContain('barTrace');
  });

  it('displays app-filter-paginate when enough results are shown', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: readonly ApiHuntResult[] =
        [...Array.from({length: 50}).keys()].map((key) => ({
                                                   clientId: `C.${key}`,
                                                   timestamp: key.toString(),
                                                   payloadType: 'foo'
                                                 }));

    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelectorAll('app-filter-paginate').length)
        .toBe(1);
  });

  it('displays one tab per result type', async () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: ReadonlyArray<ApiHuntResult> = [
      {clientId: 'C.1234', payloadType: 'foo'},
      {clientId: 'C.5678', payloadType: 'bar'}
    ];
    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const tabGroupHarness = await harnessLoader.getHarness(MatTabGroupHarness);
    expect((await tabGroupHarness.getTabs()).length).toEqual(2);

    const fooTab = (await tabGroupHarness.getTabs({label: 'foo'}))[0];
    await fooTab.select();
    expect(await fooTab.getTextContent()).toContain('C.1234');

    const barTab = (await tabGroupHarness.getTabs({label: 'bar'}))[0];
    await barTab.select();
    expect(await barTab.getTextContent()).toContain('C.5678');
  });

  it('expands translated results', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: ReadonlyArray<ApiHuntResult> = [
      {
        clientId: 'C.1234',
        payloadType: 'ClientSummary',
        payload: {
          'systemInfo': {fqdn: 'griffindor.pc'},
          'users': [{username: 'hermione'}, {username: 'neville'}]
        }
      },
      {
        clientId: 'C.5678',
        payloadType: 'ClientSummary',
        payload: {
          'systemInfo': {fqdn: 'ravenclaw.pc'},
          'users': [{username: 'luna'}]
        }
      },
      {
        clientId: 'C.999',
        payloadType: 'ClientSummary',
        payload: {},
      },
    ];
    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(3);

    enum CellIndexOf {
      CLIENT_ID = 0,
      TIMESTAMP,
      PAYLOAD_TYPE,
      OS,
      FQDN,
      NUM_USERS,
      USERNAMES,
      DETAILS_BUTTON
    }

    let cells = rows[0].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.1234');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('ClientSummary');
    expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain('griffindor.pc');
    expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('2');
    expect(cells[CellIndexOf.USERNAMES].innerText.trim())
        .toContain('hermione, neville');
    expect(cells[CellIndexOf.DETAILS_BUTTON].innerText)
        .toContain('View details');

    cells = rows[1].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.5678');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('ClientSummary');
    expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain('ravenclaw.pc');
    expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('1');
    expect(cells[CellIndexOf.USERNAMES].innerText.trim()).toContain('luna');
    expect(cells[CellIndexOf.DETAILS_BUTTON].innerText)
        .toContain('View details');

    cells = rows[2].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.999');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('ClientSummary');
    expect(cells[CellIndexOf.FQDN].innerText).toBeFalsy();
    expect(cells[CellIndexOf.NUM_USERS].innerText).toBeFalsy();
    expect(cells[CellIndexOf.USERNAMES].innerText).toBeFalsy();
    expect(cells[CellIndexOf.DETAILS_BUTTON].innerText)
        .toContain('View details');
  });

  it('expands ANOMALY type', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: ReadonlyArray<ApiHuntResult> = [
      {
        clientId: 'C.1234',
        payloadType: 'Anomaly',
        payload: {
          'type': 'UNKNOWN_ANOMALY_TYPE',
          'severity': 'VERY_HIGH',
          'confidence': 'VERY_LOW',
          'generatedBy': 'something',
        }
      },
    ];
    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(1);

    expect(rows[0].innerText.trim()).toContain('C.1234');
    expect(rows[0].innerText.trim()).toContain('UNKNOWN_ANOMALY_TYPE');
    expect(rows[0].innerText.trim()).toContain('VERY_HIGH');
    expect(rows[0].innerText.trim()).toContain('VERY_LOW');
    expect(rows[0].innerText.trim()).toContain('something');
  });

  it('expands file types', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: ReadonlyArray<ApiHuntResult> = [
      {
        clientId: 'C.0',
        payloadType: 'CollectFilesByKnownPathResult',
        payload:
            {'stat': createStatEntry(0), 'hash': {sha256: 'hash', md5: 'hash'}},
      },
      {
        clientId: 'C.1',
        payloadType: 'FileFinderResult',
        payload: {
          'statEntry': createStatEntry(1),
          'hashEntry': {md5: 'hash'},
        },
      },
      {
        clientId: 'C.2',
        payloadType: 'FileFinderResult',
        payload: {
          'statEntry': createStatEntry(2),
          'hashEntry': {sha256: 'hash'},
        },
      },
      {
        clientId: 'C.3',
        payloadType: 'StatEntry',
        payload: createStatEntry(3) as Any,
      },
    ];
    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(4);

    // CollectFilesByKnownPathResult
    expect(rows[0].innerText).toContain('C.0');
    expect(rows[0].innerText).toContain('/home/foo/bar/0');
    expect(rows[0].innerText).toContain('SHA-256 + 1');
    expect(rows[0].innerText).toContain('-rw-r--r--');
    expect(rows[0].innerText).toContain('142 B');
    expect(rows[0].innerText).toContain('1970-01-01 00:02:20 UTC');
    expect(rows[0].innerText).toContain('1970-01-01 00:23:20 UTC');
    expect(rows[0].innerText).toContain('1970-01-01 03:53:20 UTC');
    expect(rows[0].innerText).toContain('1970-01-02 14:53:20 UTC');

    // FileFinderResult
    expect(rows[1].innerText).toContain('C.1');
    expect(rows[1].innerText).toContain('/home/foo/bar/1');
    expect(rows[1].innerText).toContain('MD5');
    expect(rows[1].innerText).toContain('-rw-r--r--');
    expect(rows[1].innerText).toContain('242 B');
    expect(rows[1].innerText).toContain('1970-01-01 00:04:00 UTC');
    expect(rows[1].innerText).toContain('1970-01-01 00:40:00 UTC');
    expect(rows[1].innerText).toContain('1970-01-01 06:40:00 UTC');
    expect(rows[1].innerText).toContain('1970-01-03 18:40:00 UTC');

    expect(rows[2].innerText).toContain('C.2');
    expect(rows[2].innerText).toContain('/home/foo/bar/2');
    expect(rows[2].innerText).toContain('SHA-256');
    expect(rows[2].innerText).toContain('-rw-r--r--');
    expect(rows[2].innerText).toContain('342 B');
    expect(rows[2].innerText).toContain('1970-01-01 00:05:40 UTC');
    expect(rows[2].innerText).toContain('1970-01-01 00:56:40 UTC');
    expect(rows[2].innerText).toContain('1970-01-01 09:26:40 UTC');
    expect(rows[2].innerText).toContain('1970-01-04 22:26:40 UTC');

    // StatEntry
    expect(rows[3].innerText).toContain('C.3');
    expect(rows[3].innerText).toContain('/home/foo/bar/3');
    expect(rows[3].innerText).not.toContain('SHA-256');
    expect(rows[3].innerText).toContain('-rw-r--r--');
    expect(rows[3].innerText).toContain('442 B');
    expect(rows[3].innerText).toContain('1970-01-01 00:07:20 UTC');
    expect(rows[3].innerText).toContain('1970-01-01 01:13:20 UTC');
    expect(rows[3].innerText).toContain('1970-01-01 12:13:20 UTC');
    expect(rows[3].innerText).toContain('1970-01-06 02:13:20 UTC');
  });

  it('expands client info results', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: ReadonlyArray<ApiHuntResult> = [
      {
        clientId: 'C.1234',
        payloadType: 'ClientSummary',
        payload: {
          'systemInfo': {fqdn: 'fulano.pc', system: 'Windows'},
          'users': [{username: 'fulano'}]
        }
      },
      {
        clientId: 'C.5678',
        payloadType: 'KnowledgeBase',
        payload: {
          'os': 'Darwin',
          'fqdn': 'beltrano.mac',
          'users': [{username: 'beltrano'}]
        }
      },
    ];
    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(2);

    enum CellIndexOf {
      CLIENT_ID = 0,
      TIMESTAMP,
      PAYLOAD_TYPE,
      OS,
      FQDN,
      NUM_USERS,
      USERNAMES,
      DETAILS_BUTTON
    }

    let cells = rows[0].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.1234');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('ClientSummary');
    expect(cells[CellIndexOf.OS].innerText.trim()).toContain('Windows');
    expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain('fulano.pc');
    expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('1');
    expect(cells[CellIndexOf.USERNAMES].innerText.trim()).toContain('fulano');
    expect(cells[CellIndexOf.DETAILS_BUTTON].innerText)
        .toContain('View details');

    cells = rows[1].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.5678');
    expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim())
        .toContain('KnowledgeBase');
    expect(cells[CellIndexOf.OS].innerText.trim()).toContain('Darwin');
    expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain('beltrano.mac');
    expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('1');
    expect(cells[CellIndexOf.USERNAMES].innerText.trim()).toContain('beltrano');
    expect(cells[CellIndexOf.DETAILS_BUTTON].innerText)
        .toContain('View details');
  });

  it('expands USER type', () => {
    const fixture = TestBed.createComponent(HuntResults);
    fixture.detectChanges();

    const res: ReadonlyArray<ApiHuntResult> = [
      {
        clientId: 'C.1234',
        payloadType: 'User',
        payload: {
          'uid': 5678,
          'username': 'banana',
          'lastLogon': 1,
        }
      },
    ];
    receiveResults(huntPageGlobalStore, res);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(1);

    expect(rows[0].innerText.trim()).toContain('C.1234');
    expect(rows[0].innerText.trim()).toContain('5678');
    expect(rows[0].innerText.trim()).toContain('banana');
    expect(rows[0].innerText.trim()).toContain('1970-01-01 00:00:00 UTC');
  });
});
