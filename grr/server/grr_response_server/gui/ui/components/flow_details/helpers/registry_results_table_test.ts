import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatPaginatorHarness} from '@angular/material/paginator/testing';
import {MatSortModule} from '@angular/material/sort';
import {MatSortHarness} from '@angular/material/sort/testing';
import {MatTableHarness} from '@angular/material/table/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {RegistryKey, RegistryType, RegistryValue} from '../../../lib/models/flow';
import {initTestEnvironment} from '../../../testing';

import {HelpersModule} from './module';


initTestEnvironment();

@Component({
  template: `
    <registry-results-table
        [results]="results"
        [totalCount]="totalCount"
        (loadMore)="loadMoreTriggered()">
    </registry-results-table>`
})
class TestHostComponent {
  results?: ReadonlyArray<RegistryKey|RegistryValue>;
  totalCount?: number;

  loadMoreTriggered = jasmine.createSpy('loadMoreTriggered');
}

describe('RegistryResultsTable Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
            MatSortModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('renders the path (and type) of RegistryKeys', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.results = [
      {path: 'HKLM\\reg0', type: 'REG_KEY'},
      {path: 'HKLM\\reg1', type: 'REG_KEY'},
    ];

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTableHarness);
    const contents = await harness.getCellTextByColumnName();

    expect(contents['path'].text[0]).toContain('HKLM\\reg0');
    expect(contents['path'].text[1]).toContain('HKLM\\reg1');
    expect(contents['type'].text[0]).toEqual('REG_KEY');
    expect(contents['type'].text[1]).toEqual('REG_KEY');
  });

  it('renders the path, type, size of RegistryValues', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.results = [
      {path: 'HKLM\\reg0', type: RegistryType.REG_NONE, size: BigInt(0)},
      {path: 'HKLM\\reg1', type: RegistryType.REG_BINARY, size: BigInt(123)},
    ];

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTableHarness);
    const contents = await harness.getCellTextByColumnName();

    expect(contents['path'].text[0]).toContain('HKLM\\reg0');
    expect(contents['path'].text[1]).toContain('HKLM\\reg1');
    expect(contents['type'].text[0]).toEqual('REG_NONE');
    expect(contents['type'].text[1]).toEqual('REG_BINARY');
    expect(contents['size'].text[0]).toContain('0');
    expect(contents['size'].text[1]).toContain('123');
  });

  it('emits an event when "load more" is clicked', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results = [];
    fixture.componentInstance.totalCount = 2;
    fixture.detectChanges();

    expect(fixture.componentInstance.loadMoreTriggered).not.toHaveBeenCalled();

    const button = fixture.nativeElement.querySelector('button.load-more');
    button.click();

    expect(fixture.componentInstance.loadMoreTriggered).toHaveBeenCalled();
  });

  it('sorts results', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results =
        [...Array.from({length: 2}).keys()].map(generateKey);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(3);
    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).toContain('reg1');

    function getPaths() {
      const p1 = fixture.debugElement.query(
          By.css('tbody tr:nth-child(1) td:nth-child(1)'));
      const p2 = fixture.debugElement.query(
          By.css('tbody tr:nth-child(2) td:nth-child(1)'));
      return [
        p1.nativeElement.innerText.trim(), p2.nativeElement.innerText.trim()
      ];
    }

    expect(getPaths()).toEqual([
      jasmine.stringMatching('HKLM\\\\reg0'),
      jasmine.stringMatching('HKLM\\\\reg1')
    ]);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const sort = await harnessLoader.getHarness(MatSortHarness);
    // Sort by Path.
    const headers = await sort.getSortHeaders();
    await headers[0].click();  // asc
    await headers[0].click();  // desc

    expect(getPaths()).toEqual([
      jasmine.stringMatching('HKLM\\\\reg1'),
      jasmine.stringMatching('HKLM\\\\reg0')
    ]);
  });

  it('filters results', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results =
        [...Array.from({length: 10}).keys()].map(generateKey);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(11);
    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).toContain('reg1');

    const filterInput = fixture.debugElement.query(By.css('input'));

    // Filter is applied, selecting only the first row by process name.
    filterInput.nativeElement.value = 'reg0';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).not.toContain('reg1');

    // Filter is applied, selecting only the second row by ip address.
    filterInput.nativeElement.value = 'reg1';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toContain('reg0');
    expect(fixture.nativeElement.innerText).toContain('reg1');

    // Filter is applied, selects no row.
    filterInput.nativeElement.value = 'invalid';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).not.toContain('reg0');
    expect(fixture.nativeElement.innerText).not.toContain('reg1');
    expect(fixture.nativeElement.innerText).toContain('No data');

    // Filter is cleared, all rows are showed again.
    filterInput.nativeElement.value = '';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).toContain('reg1');
  });

  it('results are paginated', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results =
        [...Array.from({length: 12}).keys()].map(generateKey);
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('tr');
    // Rows include the header.
    expect(rows.length).toBe(11);

    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).toContain('reg9');
    expect(fixture.nativeElement.innerText).not.toContain('reg10');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginatorTop = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.top-paginator'}));
    const paginatorBottom = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.bottom-paginator'}));
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
  });

  it('paginator forward and backwards updates table contents', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results =
        [...Array.from({length: 12}).keys()].map(generateKey);
    fixture.detectChanges();

    // Rows include the header.
    expect(fixture.nativeElement.querySelectorAll('tr').length).toBe(11);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginatorTop = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.top-paginator'}));
    const paginatorBottom = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.bottom-paginator'}));

    // Second page should displays results 11-12
    await paginatorTop.goToNextPage();
    expect(fixture.nativeElement.querySelectorAll('tr').length).toBe(3);
    expect(await paginatorTop.getRangeLabel()).toBe('11 – 12 of 12');
    expect(await paginatorBottom.getRangeLabel()).toBe('11 – 12 of 12');
    expect(fixture.nativeElement.innerText).not.toContain('reg0');
    expect(fixture.nativeElement.innerText).toContain('reg11');

    // First page should displays results 1-10
    await paginatorBottom.goToFirstPage();
    expect(fixture.nativeElement.querySelectorAll('tr').length).toBe(11);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).not.toContain('reg11');
  });

  it('paginator change page size updates table contents', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.results =
        [...Array.from({length: 12}).keys()].map(generateKey);
    fixture.detectChanges();

    // Rows include the header.
    expect(fixture.nativeElement.querySelectorAll('tr').length).toBe(11);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginatorTop = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.top-paginator'}));
    const paginatorBottom = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.bottom-paginator'}));

    await paginatorTop.setPageSize(50);
    expect(fixture.nativeElement.querySelectorAll('tr').length).toBe(13);
    expect(await paginatorTop.getPageSize()).toBe(50);
    expect(await paginatorBottom.getPageSize()).toBe(50);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 12 of 12');
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 12 of 12');
    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).toContain('reg11');

    await paginatorBottom.setPageSize(10);
    expect(fixture.nativeElement.querySelectorAll('tr').length).toBe(11);
    expect(await paginatorTop.getPageSize()).toBe(10);
    expect(await paginatorBottom.getPageSize()).toBe(10);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
    expect(fixture.nativeElement.innerText).toContain('reg0');
    expect(fixture.nativeElement.innerText).not.toContain('reg11');
  });
});

function generateKey(n: number): RegistryKey {
  return {path: `HKLM\\reg${n}`, type: 'REG_KEY'};
}
