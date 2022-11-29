import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatPaginatorHarness} from '@angular/material/paginator/testing';
import {MatSortHarness} from '@angular/material/sort/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {FlowFileResult, flowFileResultFromStatEntry, StatusIcon} from '../../../components/flow_details/helpers/file_results_table';
import {createStatEntry} from '../../../lib/api/api_test_util';
import {initTestEnvironment} from '../../../testing';
import {TimestampTestingModule} from '../../timestamp/module';

import {HelpersModule} from './module';



initTestEnvironment();

// TestHostComponent is needed in order to trigger change detection in the
// underlying flow-details directive. Creating a standalone flow-details
// instance with createComponent doesn't trigger the ngOnChanges lifecycle
// hook:
// https://stackoverflow.com/questions/37408801/testing-ngonchanges-lifecycle-hook-in-angular-2
@Component({
  template: `
<file-results-table
    [results]="results"
    [totalCount]="totalCount"
    (loadMore)="loadMoreTriggered()">
</file-results-table>`
})
class TestHostComponent {
  results?: FlowFileResult[];
  totalCount?: number;

  loadMoreTriggered = jasmine.createSpy('loadMoreTriggered');
}

describe('FileResultsTable Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
            RouterTestingModule,
            TimestampTestingModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  function createComponent(results: FlowFileResult[], totalCount: number):
      ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results = results;
    fixture.componentInstance.totalCount = totalCount;
    fixture.detectChanges();

    return fixture;
  }

  it('correctly presents a single row - no Hash nor Status', () => {
    const fixture = createComponent(
        [flowFileResultFromStatEntry(createStatEntry(0))],
        1,
    );
    enum CellIndexOf { PATH = 1, MODE, SIZE, ATIME, MTIME, CTIME, BTIME }

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(2);

    const cells = rows[1].querySelectorAll('td');
    expect(cells[CellIndexOf.PATH].innerText.trim())
        .toContain('/home/foo/bar/0');
    expect(cells[CellIndexOf.MODE].innerText).toContain('-rw-r--r--');
    expect(cells[CellIndexOf.SIZE].innerText).toContain('142 B');
    expect(cells[CellIndexOf.ATIME].innerText)
        .toContain('1970-01-02 14:53:20 UTC');
    expect(cells[CellIndexOf.MTIME].innerText)
        .toContain('1970-01-17 04:53:20 UTC');
    expect(cells[CellIndexOf.CTIME].innerText)
        .toContain('1970-06-12 00:53:20 UTC');
    expect(cells[CellIndexOf.BTIME].innerText)
        .toContain('1974-06-09 08:53:20 UTC');
  });

  it('correctly presents 2 rows - Default Hash column', () => {
    const fixture = createComponent(
        [
          flowFileResultFromStatEntry(createStatEntry(0), {md5: 'hash'}),
          flowFileResultFromStatEntry(
              createStatEntry(1), {sha256: 'hash', md5: 'hash'}),
        ],
        1,
    );
    enum CellIndexOf { PATH = 1, HASH, MODE, SIZE, ATIME, MTIME, CTIME, BTIME }

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(3);

    let cells = rows[1].querySelectorAll('td');
    expect(cells[CellIndexOf.PATH].innerText.trim())
        .toContain('/home/foo/bar/0');
    expect(cells[CellIndexOf.HASH].innerText).toContain('MD5');
    expect(cells[CellIndexOf.MODE].innerText).toContain('-rw-r--r--');
    expect(cells[CellIndexOf.SIZE].innerText).toContain('142 B');
    expect(cells[CellIndexOf.ATIME].innerText)
        .toContain('1970-01-02 14:53:20 UTC');
    expect(cells[CellIndexOf.MTIME].innerText)
        .toContain('1970-01-17 04:53:20 UTC');
    expect(cells[CellIndexOf.CTIME].innerText)
        .toContain('1970-06-12 00:53:20 UTC');
    expect(cells[CellIndexOf.BTIME].innerText)
        .toContain('1974-06-09 08:53:20 UTC');

    cells = rows[2].querySelectorAll('td');
    expect(cells[CellIndexOf.PATH].innerText.trim())
        .toContain('/home/foo/bar/1');
    expect(cells[CellIndexOf.HASH].innerText).toContain('SHA-256 + 1');
    expect(cells[CellIndexOf.MODE].innerText).toContain('-rw-r--r--');
    expect(cells[CellIndexOf.SIZE].innerText).toContain('242 B');
    expect(cells[CellIndexOf.ATIME].innerText)
        .toContain('1970-01-03 18:40:00 UTC');
    expect(cells[CellIndexOf.MTIME].innerText)
        .toContain('1970-01-28 18:40:00 UTC');
    expect(cells[CellIndexOf.CTIME].innerText)
        .toContain('1970-10-05 18:40:00 UTC');
    expect(cells[CellIndexOf.BTIME].innerText)
        .toContain('1977-08-09 18:40:00 UTC');
  });

  it('correctly presents 2 rows - Status column', () => {
    const fixture = createComponent(
        [
          flowFileResultFromStatEntry(
              createStatEntry(0), undefined, {icon: StatusIcon.IN_PROGRESS}),
          flowFileResultFromStatEntry(
              createStatEntry(1), {}, {icon: StatusIcon.CHECK}),
        ],
        2,
    );
    enum CellIndexOf {
      PATH = 1,
      MODE,
      SIZE,
      ATIME,
      MTIME,
      CTIME,
      BTIME,
      STATUS,
    }

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(3);

    let cells = rows[1].querySelectorAll('td');
    expect(cells[CellIndexOf.PATH].innerText.trim())
        .toContain('/home/foo/bar/0');
    expect(cells[CellIndexOf.MODE].innerText).toContain('-rw-r--r--');
    expect(cells[CellIndexOf.SIZE].innerText).toContain('142 B');
    expect(cells[CellIndexOf.ATIME].innerText)
        .toContain('1970-01-02 14:53:20 UTC');
    expect(cells[CellIndexOf.MTIME].innerText)
        .toContain('1970-01-17 04:53:20 UTC');
    expect(cells[CellIndexOf.CTIME].innerText)
        .toContain('1970-06-12 00:53:20 UTC');
    expect(cells[CellIndexOf.BTIME].innerText)
        .toContain('1974-06-09 08:53:20 UTC');
    expect(cells[CellIndexOf.STATUS].querySelector('mat-progress-spinner'))
        .not.toBe(null);
    expect(cells[CellIndexOf.STATUS].querySelector('mat-icon')).toBe(null);

    cells = rows[2].querySelectorAll('td');
    expect(cells[CellIndexOf.PATH].innerText.trim())
        .toContain('/home/foo/bar/1');
    expect(cells[CellIndexOf.MODE].innerText).toContain('-rw-r--r--');
    expect(cells[CellIndexOf.SIZE].innerText).toContain('242 B');
    expect(cells[CellIndexOf.ATIME].innerText)
        .toContain('1970-01-03 18:40:00 UTC');
    expect(cells[CellIndexOf.MTIME].innerText)
        .toContain('1970-01-28 18:40:00 UTC');
    expect(cells[CellIndexOf.CTIME].innerText)
        .toContain('1970-10-05 18:40:00 UTC');
    expect(cells[CellIndexOf.BTIME].innerText)
        .toContain('1977-08-09 18:40:00 UTC');
    expect(cells[CellIndexOf.STATUS].innerText).toContain('check');
    expect(cells[CellIndexOf.STATUS].querySelector('mat-progress-spinner'))
        .toBe(null);
    expect(cells[CellIndexOf.STATUS].querySelector('mat-icon')).not.toBe(null);
  });


  it('does not show "load more" button when all rows are loaded', () => {
    const fixture = createComponent(
        [flowFileResultFromStatEntry(createStatEntry(0))],
        1,
    );

    expect(fixture.nativeElement.innerText).not.toContain('Load More');
  });

  it('shows "load more" button if not all rows are displayed', () => {
    const fixture = createComponent(
        [flowFileResultFromStatEntry(createStatEntry(0))],
        2,
    );

    expect(fixture.nativeElement.innerText).toContain('Load More');
  });

  it('emits an event when "load more" is clicked', () => {
    const fixture = createComponent(
        [flowFileResultFromStatEntry(createStatEntry(0))],
        2,
    );

    const button = fixture.nativeElement.querySelector('button.load-more');
    button.click();

    expect(fixture.componentInstance.loadMoreTriggered).toHaveBeenCalled();
  });

  it('uses timestamp components for dates', () => {
    const fixture = createComponent(
        [flowFileResultFromStatEntry(createStatEntry(0))],
        2,
    );
    enum CellIndexOf { ATIME = 4, MTIME, CTIME, BTIME }

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(2);
    const cells = rows[1].querySelectorAll('td');

    expect(cells[CellIndexOf.ATIME].querySelector('app-timestamp'))
        .toBeTruthy();
    expect(cells[CellIndexOf.MTIME].querySelector('app-timestamp'))
        .toBeTruthy();
    expect(cells[CellIndexOf.CTIME].querySelector('app-timestamp'))
        .toBeTruthy();
    expect(cells[CellIndexOf.BTIME].querySelector('app-timestamp'))
        .toBeTruthy();
  });

  it('uses human-readable-size components for the size', () => {
    const fixture = createComponent(
        [flowFileResultFromStatEntry(createStatEntry(0))],
        2,
    );
    const SIZE_INDEX = 3;

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(2);
    const cells = rows[1].querySelectorAll('td');

    expect(cells[SIZE_INDEX].querySelector('human-readable-size')).toBeTruthy();
  });

  it('filters results', () => {
    const fixture = createComponent(
        [...new Array(10)].map(
            (v, i) => flowFileResultFromStatEntry(createStatEntry(i))),
        10,
    );

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(11);
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/0');
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/1');

    const filterInput = fixture.debugElement.query(By.css('input'));

    // Filter is applied, selecting only the first row by process name.
    filterInput.nativeElement.value = '/home/foo/bar/0';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/0');
    expect(fixture.nativeElement.innerText).not.toContain('/home/foo/bar/1');

    // Filter is applied, selecting only the second row by ip address.
    filterInput.nativeElement.value = '/home/foo/bar/1';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toContain('/home/foo/bar/0');
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/1');

    // Filter is applied, selects no row.
    filterInput.nativeElement.value = 'invalid';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toContain('/home/foo/bar/0');
    expect(fixture.nativeElement.innerText).not.toContain('/home/foo/bar/1');
    expect(fixture.nativeElement.innerText).toContain('No data');

    // Filter is cleared, all rows are showed again.
    filterInput.nativeElement.value = '';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/0');
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/1');
  });


  it('sorts results', async () => {
    const fixture = createComponent(
        [
          flowFileResultFromStatEntry(createStatEntry(0)),
          flowFileResultFromStatEntry(createStatEntry(1))
        ],
        2,
    );

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(3);
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/0');
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/1');

    function getFileNames() {
      const p1 = fixture.debugElement.query(
          By.css('tbody tr:nth-child(1) td:nth-child(2)'));
      const p2 = fixture.debugElement.query(
          By.css('tbody tr:nth-child(2) td:nth-child(2)'));
      return [
        p1.nativeElement.innerText.trim(), p2.nativeElement.innerText.trim()
      ];
    }

    expect(getFileNames()).toEqual([
      jasmine.stringMatching('/home/foo/bar/0'),
      jasmine.stringMatching('/home/foo/bar/1')
    ]);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const sort = await harnessLoader.getHarness(MatSortHarness);
    // Sort by Path.
    const headers = await sort.getSortHeaders();
    await headers[0].click();  // asc
    await headers[0].click();  // desc

    expect(getFileNames()).toEqual([
      jasmine.stringMatching('/home/foo/bar/1'),
      jasmine.stringMatching('/home/foo/bar/0')
    ]);
  });

  it('default pagination works', async () => {
    const fixture = createComponent(
        Array.from(
            {length: 12},
            (v, i) => flowFileResultFromStatEntry(createStatEntry(i))),
        1,
    );
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginatorTop = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.top-paginator'}));
    const paginatorBottom = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.bottom-paginator'}));

    // Paginators start with default values, 0-9 are shown, but 10 isn't.
    expect(await paginatorTop.getPageSize()).toBe(10);
    expect(await paginatorBottom.getPageSize()).toBe(10);
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/0');
    expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/9');
    expect(fixture.nativeElement.innerText).not.toContain('/home/foo/bar/10');
  });

  it('clicking TOP paginator updates bottom paginator state (page size)',
     async () => {
       const fixture = createComponent(
           [...new Array(55)].map(
               (v, i) => flowFileResultFromStatEntry(createStatEntry(i))),
           1,
       );

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const paginatorTop = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.top-paginator'}));
       const paginatorBottom = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.bottom-paginator'}));

       // Change page size on top paginator should update the bottom paginator.
       await paginatorTop.setPageSize(50);
       expect(await paginatorTop.getPageSize()).toBe(50);
       expect(await paginatorBottom.getPageSize()).toBe(50);
       expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 55');
       expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 55');
       expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/0');
       expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/49');
     });

  it('clicking BOTTOM paginator updates bottom paginator state (page size)',
     async () => {
       const fixture = createComponent(
           Array.from(
               {length: 55},
               (v, i) => flowFileResultFromStatEntry(createStatEntry(i))),
           1,
       );

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const paginatorTop = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.top-paginator'}));
       const paginatorBottom = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.bottom-paginator'}));

       // Change page size on bottom paginator should update the top paginator.
       await paginatorBottom.setPageSize(50);
       expect(await paginatorTop.getPageSize()).toBe(50);
       expect(await paginatorBottom.getPageSize()).toBe(50);
       expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 55');
       expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 55');
       expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/0');
       expect(fixture.nativeElement.innerText).toContain('/home/foo/bar/49');
     });
});
