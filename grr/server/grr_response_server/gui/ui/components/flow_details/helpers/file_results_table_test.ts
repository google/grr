import {Component} from '@angular/core';
import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowFileResult, flowFileResultFromStatEntry} from '@app/components/flow_details/helpers/file_results_table';
import {StatEntry} from '@app/lib/api/api_interfaces';
import {newPathSpec} from '@app/lib/api/api_test_util';
import {initTestEnvironment} from '@app/testing';
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
  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
          ],
          declarations: [
            TestHostComponent,
          ],

          providers: []
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

  function createStatEntry(index: number): StatEntry {
    return {
      pathspec: newPathSpec(`/home/foo/bar/${index}`),
      stMode: '420',  // 0644
      stDev: 16777220 + index,
      stNlink: 1 + index,
      stUid: 237586 + index,
      stGid: 89939 + index,
      stSize: `${index + 1}42`,
      stAtime: `${index + 1}40000`,
      stMtime: `${index + 1}400000`,
      stCtime: `${index + 1}4000000`,
    };
  }

  it('correctly presents a single row', () => {
    const fixture = createComponent(
        [flowFileResultFromStatEntry(createStatEntry(0))],
        1,
    );

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(2);

    const cells = rows[1].querySelectorAll('td');
    expect(cells[0].innerText).toBe('/home/foo/bar/0');
    expect(cells[1].innerText).toBe('-rw-r--r--');
    expect(cells[2].innerText).toBe('237586');
    expect(cells[3].innerText).toBe('89939');
    expect(cells[4].innerText).toBe('142');
    expect(cells[5].innerText).toBe('1970-01-02 02:53:20');
    expect(cells[6].innerText).toBe('1970-01-17 04:53:20');
    expect(cells[7].innerText).toBe('1970-06-12 12:53:20');
  });

  it('correctly presents 2 rows', () => {
    const fixture = createComponent(
        [
          flowFileResultFromStatEntry(createStatEntry(0)),
          flowFileResultFromStatEntry(createStatEntry(1)),
        ],
        1,
    );

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(3);

    let cells = rows[1].querySelectorAll('td');
    expect(cells[0].innerText).toBe('/home/foo/bar/0');
    expect(cells[1].innerText).toBe('-rw-r--r--');
    expect(cells[2].innerText).toBe('237586');
    expect(cells[3].innerText).toBe('89939');
    expect(cells[4].innerText).toBe('142');
    expect(cells[5].innerText).toBe('1970-01-02 02:53:20');
    expect(cells[6].innerText).toBe('1970-01-17 04:53:20');
    expect(cells[7].innerText).toBe('1970-06-12 12:53:20');

    cells = rows[2].querySelectorAll('td');
    expect(cells[0].innerText).toBe('/home/foo/bar/1');
    expect(cells[1].innerText).toBe('-rw-r--r--');
    expect(cells[2].innerText).toBe('237587');
    expect(cells[3].innerText).toBe('89940');
    expect(cells[4].innerText).toBe('242');
    expect(cells[5].innerText).toBe('1970-01-03 06:40:00');
    expect(cells[6].innerText).toBe('1970-01-28 06:40:00');
    expect(cells[7].innerText).toBe('1970-10-05 06:40:00');
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
});
