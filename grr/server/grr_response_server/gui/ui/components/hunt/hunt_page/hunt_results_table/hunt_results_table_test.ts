import {Component, ViewChild} from '@angular/core';
import {
  TestBed,
  discardPeriodicTasks,
  fakeAsync,
  tick,
  waitForAsync,
} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ApiHuntError, ApiHuntResult} from '../../../../lib/api/api_interfaces';
import {createStatEntry} from '../../../../lib/api/api_test_util';
import {HttpApiService} from '../../../../lib/api/http_api_service';
import {
  HttpApiServiceMock,
  injectHttpApiServiceMock,
  mockHttpApiService,
} from '../../../../lib/api/http_api_service_test_util';
import {HexHash} from '../../../../lib/models/flow';
import {HuntResultOrError} from '../../../../lib/models/result';
import {initTestEnvironment} from '../../../../testing';

import {HuntResultsTable, RESULTS_BATCH_SIZE} from './hunt_results_table';

const mockHuntResult: ApiHuntResult = {
  clientId: 'mockClientId',
  timestamp: '1669027009243432',
};

/**
 * Generates a list of Hunt Results from a base Hunt Result object, by only
 * changes the timestamp property of each.
 *
 * @param result: Base result object to use to generate the output list.
 * @param size: The number of results to be returned.
 */
function generateResultListFromResult<T extends HuntResultOrError>(
  result: T,
  size: number,
): T[] {
  const timeDeltaBetweenResults = 1_000_000;

  const res: T[] = [];

  for (let i = 1; i <= size; i++) {
    res.push({
      ...result,
      timestamp: `${Number(result.timestamp) + timeDeltaBetweenResults * i}`,
    });
  }

  return res;
}

initTestEnvironment();

@Component({
  standalone: false,
  template: `<app-hunt-results-table
      [huntId]="huntId"
      [totalResultsCount]="totalResultsCount"
      [resultType]="resultType"
      (selectedHuntResult)="selectedHuntResult($event)">
    </app-hunt-results-table>`,
  jit: true,
})
class TestHostComponent {
  huntId: string | undefined = '1984';
  totalResultsCount = 0;
  resultType = 'User';

  @ViewChild(HuntResultsTable)
  resultsTable!: HuntResultsTable<ApiHuntResult | ApiHuntError>;

  selectedHuntResult(result: ApiHuntResult | ApiHuntError): void {}
}

describe('HuntResultsTable', () => {
  let httpApiService: HttpApiServiceMock;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HuntResultsTable, NoopAnimationsModule],
      declarations: [TestHostComponent],
      providers: [{provide: HttpApiService, useFactory: mockHttpApiService}],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    httpApiService = injectHttpApiServiceMock();
  }));

  describe('Table row number', () => {
    it('Table shows nothing as no hunt id was specified', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      component.huntId = undefined;

      fixture.detectChanges();

      expect(
        fixture.debugElement.query(By.css('.load-more-container')),
      ).toBeNull();
      expect(fixture.debugElement.query(By.css('mat-table'))).toBeNull();
      expect(fixture.nativeElement.innerText).toEqual('No Hunt specified');
    });

    it('Table shows nothing as the number of results is 0', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      expect(
        fixture.debugElement.query(By.css('.load-more-container')),
      ).toBeNull();
      expect(fixture.debugElement.query(By.css('mat-table'))).toBeNull();
      expect(fixture.nativeElement.innerText).toEqual(
        'There are no results to show',
      );
    });

    it('Table shows nothing as the API call returned 0 results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.totalResultsCount = 10;
      component.resultType = 'User';

      fixture.detectChanges();

      tick();

      // Despite totalResultsCount being 10, the API call returns no results:
      httpApiService.mockedObservables.listResultsForHunt.next([]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).toBeNull();

      expect(fixture.nativeElement.innerText).toEqual(
        `User results could not be loaded.`,
      );

      discardPeriodicTasks();
    }));

    it('Table shows a total of 10 results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      component.totalResultsCount = 10;

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        generateResultListFromResult(mockHuntResult, 10),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        10,
      );

      discardPeriodicTasks();
    }));

    it('Updates the table dynamically after receiving a new totalResultsCount', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockResults = generateResultListFromResult(mockHuntResult, 10);

      // We have a total of 5 results:
      component.totalResultsCount = 5;

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        mockResults.slice(0, 5),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        5,
      );

      // Now we have a total of 10 results:
      component.totalResultsCount = 10;

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        mockResults.slice(5, 10),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        10,
      );

      discardPeriodicTasks();
    }));

    it('Shows the available amount of results as rows despite totalResultsCount being bigger', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockResults = generateResultListFromResult(mockHuntResult, 10);

      // We have a total of 5 results:
      component.totalResultsCount = 5;

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        mockResults.slice(0, 5),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        5,
      );

      // Now we have a total of 10 results:
      component.totalResultsCount = 10;

      // But the api call returns 3 more items, instead of 5.
      httpApiService.mockedObservables.listResultsForHunt.next(
        mockResults.slice(5, 8),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        8,
      );

      discardPeriodicTasks();
    }));

    it('Shows the available amount of results as rows despite totalResultsCount being smaller', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockResults = generateResultListFromResult(mockHuntResult, 10);

      // We have a total of 5 results:
      component.totalResultsCount = 5;

      fixture.detectChanges();

      tick();

      // But the Api call returns 10:
      httpApiService.mockedObservables.listResultsForHunt.next(mockResults);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        10,
      );

      discardPeriodicTasks();
    }));

    it('Resets the results count if the huntId or result type change', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      // We have a total of 10 results:
      component.totalResultsCount = 10;
      component.huntId = '1984';
      component.resultType = 'User';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        generateResultListFromResult(mockHuntResult, 10),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        10,
      );

      // now we have a total of 5 results of another hunt and result type:
      component.totalResultsCount = 5;
      component.huntId = '2023';
      component.resultType = 'FileFinderResult';

      const mockFileFinderResult = {
        clientId: 'C.mockClientId',
        payload: {
          '@type':
            'type.googleapis.com/grr.FileFinderResult',
          'statEntry': createStatEntry(1),
          'hashEntry': {md5: 'hash'},
        },
        timestamp: '1669027009243432',
      };

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        generateResultListFromResult(mockFileFinderResult, 5),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        5,
      );

      discardPeriodicTasks();
    }));

    it('Resets the table if the huntId or result type change', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      // We have a total of 10 results:
      component.totalResultsCount = 10;
      component.huntId = '1984';
      component.resultType = 'User';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        generateResultListFromResult(mockHuntResult, 10),
      );

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();
      expect(fixture.debugElement.queryAll(By.css('mat-row')).length).toEqual(
        10,
      );

      // now we have a total of 5 results of another hunt and result type:
      component.totalResultsCount = 5;
      component.huntId = '2023';
      component.resultType = 'FileFinderResult';

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).toBeNull();

      discardPeriodicTasks();
    }));
  });

  describe('Load more', () => {
    it('button is not shown if there are no results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      // We have a total of 0 results:
      component.totalResultsCount = 0;

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([]);

      fixture.detectChanges();

      const loadMoreButton = fixture.debugElement.query(
        By.css('.load-more-container [name=LoadMoreButton]'),
      );
      expect(loadMoreButton).toBeNull();

      const loadMoreSubtitle = fixture.debugElement.query(
        By.css('.load-more-container .subtitle'),
      );
      expect(loadMoreSubtitle).toBeNull();

      expect(fixture.nativeElement.innerText).toEqual(
        'There are no results to show',
      );

      discardPeriodicTasks();
    }));

    it('Shows the correct total number of items when totalResultsCount and the results count are inconsistent', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockResults = generateResultListFromResult(mockHuntResult, 10);

      // We have a total of 5 results:
      component.totalResultsCount = 5;

      fixture.detectChanges();

      tick();

      // But the Api call returns 10:
      httpApiService.mockedObservables.listResultsForHunt.next(mockResults);

      fixture.detectChanges();

      const loadMoreButton = fixture.debugElement.query(
        By.css('.load-more-container [name=LoadMoreButton]'),
      );

      expect(loadMoreButton).not.toBeNull();
      expect(loadMoreButton.nativeElement.getAttribute('disabled')).toEqual(
        'true',
      );
      expect(loadMoreButton.nativeElement.innerText).toEqual(
        'Nothing more to load',
      );

      const loadMoreSubtitle = fixture.debugElement.query(
        By.css('.load-more-container .subtitle'),
      );
      expect(loadMoreSubtitle).not.toBeNull();
      expect(loadMoreSubtitle.nativeElement.innerText).toEqual(
        '(displaying 10 out of 10 results)',
      );

      discardPeriodicTasks();
    }));

    it('is disabled if there are no more items to load', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      // We have a total of 30 results:
      component.totalResultsCount = 30;

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next(
        generateResultListFromResult(mockHuntResult, 30),
      );

      fixture.detectChanges();

      const loadMoreButton = fixture.debugElement.query(
        By.css('.load-more-container [name=LoadMoreButton]'),
      );

      expect(loadMoreButton).not.toBeNull();
      expect(loadMoreButton.nativeElement.getAttribute('disabled')).toEqual(
        'true',
      );
      expect(loadMoreButton.nativeElement.innerText).toEqual(
        'Nothing more to load',
      );

      const loadMoreSubtitle = fixture.debugElement.query(
        By.css('.load-more-container .subtitle'),
      );
      expect(loadMoreSubtitle.nativeElement.innerText).toEqual(
        '(displaying 30 out of 30 results)',
      );

      discardPeriodicTasks();
    }));

    it('loads more items after button click', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;

      const mockResults = generateResultListFromResult(mockHuntResult, 80);

      // We have a total of 100 results:
      component.totalResultsCount = 80;

      fixture.detectChanges();

      // The component loads up to RESULTS_BATCH_SIZE results automatically.
      // After that it needs user action (Load more action)
      httpApiService.mockedObservables.listResultsForHunt.next(
        mockResults.slice(0, RESULTS_BATCH_SIZE),
      );

      fixture.detectChanges();

      const loadMoreButton = fixture.debugElement.query(
        By.css('.load-more-container [name=LoadMoreButton]'),
      );

      expect(loadMoreButton).not.toBeNull();
      expect(
        loadMoreButton.nativeElement.getAttribute('disabled'),
      ).not.toBeTruthy();
      expect(loadMoreButton.nativeElement.innerText).toEqual('Load 30 more');

      const loadMoreSubtitle = fixture.debugElement.query(
        By.css('.load-more-container .subtitle'),
      );
      expect(loadMoreSubtitle.nativeElement.innerText).toEqual(
        `(displaying ${RESULTS_BATCH_SIZE} out of 80 results)`,
      );

      httpApiService.mockedObservables.listResultsForHunt.next(
        mockResults.slice(RESULTS_BATCH_SIZE, 80),
      );

      loadMoreButton.nativeElement.click();

      fixture.detectChanges();

      expect(loadMoreButton.nativeElement.getAttribute('disabled')).toEqual(
        'true',
      );
      expect(loadMoreSubtitle.nativeElement.innerText).toEqual(
        '(displaying 80 out of 80 results)',
      );

      discardPeriodicTasks();
    }));
  });

  describe('Table columns', () => {
    it('correctly renders "base" type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockBaseHuntResult: ApiHuntResult = {
        clientId: 'C.mockClientId',
        timestamp: '1669027009243432',
        payload: {
          '@type': 'type.googleapis.com/grr.User',
          'uid': 5678,
          'username': 'banana',
        },
      };

      component.totalResultsCount = 1;
      component.resultType = 'User';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockBaseHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);
      expect(rows[0].innerText).toContain('C.mockClientId');
      expect(rows[0].innerText).toContain('2022-11-21 10:36:49 UTC');
      expect(rows[0].innerText).toContain('User');
      expect(rows[0].innerText).toContain('View details');

      discardPeriodicTasks();
    }));

    it('correctly renders "FileFinderResult" type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockBaseHuntResult: ApiHuntResult = {
        clientId: 'C.mockClientId',
        payload: {
          '@type':
            'type.googleapis.com/grr.FileFinderResult',
          'statEntry': createStatEntry(1),
          'hashEntry': {md5: 'hash'},
        },
        timestamp: '1669027009243432',
      };

      component.totalResultsCount = 1;
      component.resultType = 'FileFinderResult';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockBaseHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      expect(rows[0].innerText).toContain('C.mockClientId');
      expect(rows[0].innerText).toContain('/home/foo/bar/1');
      expect(rows[0].innerText).toContain('MD5');
      expect(rows[0].innerText).toContain('-rw-r--r--');
      expect(rows[0].innerText).toContain('242 B');
      expect(rows[0].innerText).toContain('2023-03-29 20:00:00 UTC');
      expect(rows[0].innerText).toContain('2023-03-29 20:16:40 UTC');
      expect(rows[0].innerText).toContain('2023-03-29 20:33:20 UTC');
      expect(rows[0].innerText).toContain('2023-03-29 20:50:00 UTC');

      const rowItem = component.resultsTable.dataSource.data[0];

      expect(rowItem.rowData['hash'] as HexHash).toEqual(
        jasmine.objectContaining({md5: '85ab21'}),
      );

      discardPeriodicTasks();
    }));

    it('correctly renders "ClientSummary" type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockBaseHuntResult: ApiHuntResult = {
        clientId: 'C.1234',
        payload: {
          '@type': 'type.googleapis.com/grr.ClientSummary',
          'value': 'some value',
          'systemInfo': {fqdn: 'griffindor.pc'},
          'users': [{username: 'hermione'}, {username: 'neville'}],
        },
      };

      component.totalResultsCount = 1;
      component.resultType = 'ClientSummary';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockBaseHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      enum CellIndexOf {
        CLIENT_ID = 0,
        TIMESTAMP,
        PAYLOAD_TYPE,
        OS,
        FQDN,
        NUM_USERS,
        USERNAMES,
        DETAILS_BUTTON,
      }

      const cells = rows[0].querySelectorAll('mat-cell');
      expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.1234');
      expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim()).toContain(
        'ClientSummary',
      );
      expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain(
        'griffindor.pc',
      );
      expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('2');
      expect(cells[CellIndexOf.USERNAMES].innerText.trim()).toContain(
        'hermione, neville',
      );
      expect(cells[CellIndexOf.DETAILS_BUTTON].innerText).toContain(
        'View details',
      );

      discardPeriodicTasks();
    }));

    it('correctly renders "KnowledgeBase" type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockKnowledgeBaseHuntResult: ApiHuntResult = {
        clientId: 'C.5678',
        payload: {
          '@type': 'type.googleapis.com/grr.KnowledgeBase',
          'os': 'Darwin',
          'fqdn': 'beltrano.mac',
          'users': [{username: 'beltrano'}],
        },
      };

      component.totalResultsCount = 1;
      component.resultType = 'KnowledgeBase';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockKnowledgeBaseHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      enum CellIndexOf {
        CLIENT_ID = 0,
        TIMESTAMP,
        PAYLOAD_TYPE,
        OS,
        FQDN,
        NUM_USERS,
        USERNAMES,
        DETAILS_BUTTON,
      }

      const cells = rows[0].querySelectorAll('mat-cell');
      expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.5678');
      expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim()).toContain(
        'KnowledgeBase',
      );
      expect(cells[CellIndexOf.OS].innerText.trim()).toContain('Darwin');
      expect(cells[CellIndexOf.FQDN].innerText.trim()).toContain(
        'beltrano.mac',
      );
      expect(cells[CellIndexOf.NUM_USERS].innerText.trim()).toContain('1');
      expect(cells[CellIndexOf.USERNAMES].innerText.trim()).toContain(
        'beltrano',
      );
      expect(cells[CellIndexOf.DETAILS_BUTTON].innerText).toContain(
        'View details',
      );

      discardPeriodicTasks();
    }));

    it('correctly renders "User" type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockUserHuntResult: ApiHuntResult = {
        clientId: 'C.1234',
        payload: {
          '@type': 'type.googleapis.com/grr.User',
          'uid': 5678,
          'username': 'banana',
          'lastLogon': 1,
        },
      };

      component.totalResultsCount = 1;
      component.resultType = 'User';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockUserHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      expect(rows[0].innerText.trim()).toContain('C.1234');
      expect(rows[0].innerText.trim()).toContain('5678');
      expect(rows[0].innerText.trim()).toContain('banana');
      expect(rows[0].innerText.trim()).toContain('1970-01-01 00:00:00 UTC');

      discardPeriodicTasks();
    }));

    it('correctly renders "ExecutePythonHackResult" type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockUserHuntResult: ApiHuntResult = {
        clientId: 'C.1234',
        payload: {
          '@type':
            'type.googleapis.com/grr.ExecutePythonHackResult',
          'resultString': 'potato',
        },
      };

      component.totalResultsCount = 1;
      component.resultType = 'ExecutePythonHackResult';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockUserHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      expect(rows[0].innerText.trim()).toContain('C.1234');
      expect(rows[0].innerText.trim()).toContain('potato');

      discardPeriodicTasks();
    }));

    it('correctly renders "ExecuteBinaryResponse" type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockHuntResult: ApiHuntResult = {
        clientId: 'C.1234',
        payload: {
          '@type':
            'type.googleapis.com/grr.ExecuteBinaryResponse',
          'exitStatus': 0,
          'stdout': btoa("I'm out"),
          'stderr': btoa("I'm groot"),
        },
      };

      component.totalResultsCount = 1;
      component.resultType = 'ExecuteBinaryResponse';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      expect(rows[0].innerText.trim()).toContain('C.1234');
      expect(rows[0].innerText.trim()).toContain('0');
      expect(rows[0].innerText.trim()).toContain("I'm out");
      expect(rows[0].innerText.trim()).toContain("I'm groot");

      discardPeriodicTasks();
    }));

    it('correctly renders "ERRORS" results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockHuntError: ApiHuntError = {
        clientId: 'C.1234',
        logMessage: 'fooLog',
        backtrace: 'fooTrace',
        timestamp: '1677685676900226',
      };

      component.totalResultsCount = 1;
      component.resultType = 'ApiHuntError';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listErrorsForHunt.next([mockHuntError]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      enum CellIndexOf {
        CLIENT_ID = 0,
        TIMESTAMP,
        PAYLOAD_TYPE,
        LOG_MESSAGE,
        BACKTRACE,
        DETAILS_BUTTON,
      }

      const cells = rows[0].querySelectorAll('mat-cell');
      expect(cells[CellIndexOf.CLIENT_ID].innerText.trim()).toContain('C.1234');
      expect(
        cells[CellIndexOf.TIMESTAMP].querySelectorAll('app-timestamp').length,
      ).toBe(1);
      expect(cells[CellIndexOf.PAYLOAD_TYPE].innerText.trim()).toContain(
        'ApiHuntError',
      );
      expect(cells[CellIndexOf.LOG_MESSAGE].innerText.trim()).toContain(
        'fooLog',
      );
      expect(cells[CellIndexOf.BACKTRACE].innerText.trim()).toContain(
        'fooTrace',
      );
      expect(cells[CellIndexOf.DETAILS_BUTTON].innerText.trim()).toContain(
        'View details',
      );

      discardPeriodicTasks();
    }));

    it('correctly renders unknown type results', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockBaseHuntResult: ApiHuntResult = {
        clientId: 'C.mockClientId',
        payload: {
          '@type':
            'type.googleapis.com/grr.SomeNewResultType',
        },
        timestamp: '1669027009243432',
      };

      component.totalResultsCount = 1;
      component.resultType = 'SomeNewResultType';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockBaseHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);
      expect(rows[0].innerText).toContain('C.mockClientId');
      expect(rows[0].innerText).toContain('2022-11-21 10:36:49 UTC');
      expect(rows[0].innerText).toContain('SomeNewResultType');
      expect(rows[0].innerText).toContain('View details');

      discardPeriodicTasks();
    }));
  });

  describe('View Details button', () => {
    it('emits an event to the parent component when clicked on a Result row', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockBaseHuntResult: ApiHuntResult = {
        clientId: 'C.mockClientId',
        timestamp: '1669027009243432',
      };

      component.totalResultsCount = 1;
      component.resultType = 'User';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listResultsForHunt.next([
        mockBaseHuntResult,
      ]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      const button = fixture.nativeElement.querySelector(
        '.view-details-button',
      );

      expect(button).not.toBeNull();
      expect(button.innerText).toContain('View details');

      const eventListenerSpy = spyOn(component, 'selectedHuntResult');

      button.click();

      expect(eventListenerSpy).toHaveBeenCalledWith(mockBaseHuntResult);

      discardPeriodicTasks();
    }));

    it('emits an event to the parent component when clicked on an Error row', fakeAsync(() => {
      const fixture = TestBed.createComponent(TestHostComponent);
      const component = fixture.componentInstance;
      const mockHuntError: ApiHuntError = {
        clientId: 'C.mockClientId',
        timestamp: '1669027009243432',
        backtrace: 'fooTrace',
        logMessage: 'Something went wrong.',
      };

      component.totalResultsCount = 1;
      component.resultType = 'ApiHuntError';

      fixture.detectChanges();

      tick();

      httpApiService.mockedObservables.listErrorsForHunt.next([mockHuntError]);

      fixture.detectChanges();

      expect(fixture.debugElement.query(By.css('mat-table'))).not.toBeNull();

      const rows = fixture.nativeElement.querySelectorAll('mat-row');

      expect(rows.length).toBe(1);

      const button = fixture.nativeElement.querySelector(
        '.view-details-button',
      );

      expect(button).not.toBeNull();
      expect(button.innerText).toContain('View details');

      const eventListenerSpy = spyOn(component, 'selectedHuntResult');

      button.click();

      expect(eventListenerSpy).toHaveBeenCalledWith(mockHuntError);

      discardPeriodicTasks();
    }));
  });
});
