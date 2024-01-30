// g3-format-changed-lines-during-prettier-version-upgrade
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatPaginatorHarness} from '@angular/material/paginator/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';
import {ReplaySubject} from 'rxjs';

import {StatEntry} from '../../../lib/api/api_interfaces';
import {createStatEntry} from '../../../lib/api/api_test_util';
import {
  FlowResult,
  ResultSource,
  ResultTypeQuery,
} from '../../../lib/models/flow';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';
import {
  HuntPageGlobalStoreMock,
  mockHuntPageGlobalStore,
} from '../../../store/hunt_page_global_store_test_util';
import {STORE_PROVIDERS} from '../../../store/store_test_providers';
import {initTestEnvironment} from '../../../testing';

import {DataTableView} from './table';

initTestEnvironment();

function mockResultSource() {
  return {
    results$: new ReplaySubject<FlowResult[]>(1),
    totalCount$: new ReplaySubject<number>(1),
    query$: new ReplaySubject<ResultTypeQuery>(1),
    loadResults: jasmine.createSpy('loadResult'),
  };
}

describe('DataTableView component', () => {
  let huntPageGlobalStore: HuntPageGlobalStoreMock;
  let resultSource = mockResultSource();

  beforeEach(waitForAsync(() => {
    huntPageGlobalStore = mockHuntPageGlobalStore();
    resultSource = mockResultSource();
    TestBed.configureTestingModule({
      imports: [
        DataTableView,
        NoopAnimationsModule,
        RouterTestingModule.withRoutes([
          // Dummy route to stop error when navigating to details.
          {
            outlet: 'drawer',
            path: 'result-details/:id',
            component: DataTableView,
          },
        ]),
      ],
      providers: [...STORE_PROVIDERS],
      teardown: {destroyAfterEach: false},
    })
      .overrideProvider(HuntPageGlobalStore, {
        useFactory: () => huntPageGlobalStore,
      })
      .overrideProvider(ResultSource, {
        useFactory: () => resultSource as ResultSource<unknown>,
      })
      .compileComponents();
  }));

  it('displays translated flow results', () => {
    const fixture = TestBed.createComponent(DataTableView);
    resultSource.totalCount$.next(2);
    resultSource.query$.next({type: 'StatEntry'});
    fixture.detectChanges();

    resultSource.results$.next([
      {
        timestamp: new Date(1234),
        payloadType: 'StatEntry',
        tag: '',
        payload: createStatEntry(3),
      },
      {
        timestamp: new Date(5678),
        payloadType: 'StatEntry',
        tag: '',
        payload: {pathspec: {path: '/bar'}} as StatEntry,
      },
    ]);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('mat-row');
    expect(rows.length).toBe(2);

    enum CellIndexOf {
      PATH = 0,
      FILE_MODE,
      HASH,
      HUMAN_READABLE_SIZE,
      TIMESTAMP,
    }

    let cells = rows[0].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.PATH].innerText).toContain('/foo');
    expect(cells[CellIndexOf.FILE_MODE].innerText).toContain('-rw-r--r--');
    expect(cells[CellIndexOf.HUMAN_READABLE_SIZE].innerText).toContain('442 B');
    expect(cells[CellIndexOf.TIMESTAMP].innerText).toContain(
      '2023-03-30 01:33:20 UTC',
    );

    cells = rows[1].querySelectorAll('mat-cell');
    expect(cells[CellIndexOf.PATH].innerText).toContain('/bar');
  });

  it('shows total result count', async () => {
    const fixture = TestBed.createComponent(DataTableView);
    resultSource.totalCount$.next(123);
    fixture.detectChanges();

    // For unknown, mystical, and elusive reasons, Angular's MatPaginator keeps
    // showing "0 of 0" unless the MatPaginatorHarness is loaded.
    // MatPaginator should show the count of 123 in tests without it, but
    // weirdly doesn't. Also, loading the harness should be a no-op, but also
    // isn't.
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    await harnessLoader.getHarness(MatPaginatorHarness);

    expect(fixture.debugElement.nativeElement.textContent).toContain('123');
  });

  it('queries initial result page', async () => {
    const fixture = TestBed.createComponent(DataTableView);
    resultSource.totalCount$.next(50);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginationHarness = await harnessLoader.getHarness(
      MatPaginatorHarness,
    );
    const pageSize = await paginationHarness.getPageSize();

    expect(resultSource.loadResults).toHaveBeenCalledOnceWith({
      offset: 0,
      count: pageSize,
    });
  });

  it('queries next page upon pagination', async () => {
    const fixture = TestBed.createComponent(DataTableView);
    resultSource.totalCount$.next(50);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginationHarness = await harnessLoader.getHarness(
      MatPaginatorHarness,
    );
    await paginationHarness.goToNextPage();

    const pageSize = await paginationHarness.getPageSize();

    expect(resultSource.loadResults).toHaveBeenCalledWith({
      offset: pageSize,
      count: pageSize,
    });
  });
});
