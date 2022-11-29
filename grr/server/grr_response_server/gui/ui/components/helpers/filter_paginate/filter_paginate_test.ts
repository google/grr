import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatPaginatorHarness} from '@angular/material/paginator/testing';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {FilterPaginate} from './filter_paginate';


initTestEnvironment();

declare interface DummyRow {
  content: string;
}

@Component({
  template: `
<app-filter-paginate [dataSource]="dataSource" [dataLength]="dataLength">
  <table mat-table [dataSource]="dataSource">
    <ng-container matColumnDef="content">
      <td mat-cell *matCellDef="let r" class="cell">
        {{r.content}}
      </td>
      <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
    </ng-container>
  </table>
</app-filter-paginate>`
})
class TestHostComponent {
  dataSource?: MatTableDataSource<DummyRow>;
  dataLength?: number = 0;
  displayedColumns: string[] = ['content'];
}

describe('FilterPaginate Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            FilterPaginate,
            MatTableModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: []
        })
        .compileComponents();
  }));

  function generateRow(i: number): DummyRow {
    const content = `row${i}`;
    return {content};
  }

  function generateTableData(length: number) {
    const source = new MatTableDataSource<DummyRow>();
    source.data = Array.from({length}, (v, i) => generateRow(i));
    return source;
  }

  function createComponent(
      dataSource: MatTableDataSource<DummyRow>,
      dataLength: number|undefined): ComponentFixture<TestHostComponent> {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.dataSource = dataSource;
    fixture.componentInstance.dataLength = dataLength;
    fixture.detectChanges();
    return fixture;
  }

  it('filters results', () => {
    const fixture = createComponent(generateTableData(10), 10);

    const rows = fixture.nativeElement.querySelectorAll('tr');
    expect(rows.length).toBe(10);
    expect(fixture.nativeElement.innerText).toContain('row0');
    expect(fixture.nativeElement.innerText).toContain('row1');

    const filterInput = fixture.debugElement.query(By.css('input'));

    // Filter is applied, selecting only the first row.
    filterInput.nativeElement.value = 'row0';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('row0');
    expect(fixture.nativeElement.innerText).not.toContain('row1');

    // Filter is cleared, all rows are showed again.
    filterInput.nativeElement.value = '';
    filterInput.triggerEventHandler(
        'input', {target: filterInput.nativeElement});
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText).toContain('row0');
    expect(fixture.nativeElement.innerText).toContain('row1');
  });

  it('default pagination works', async () => {
    const fixture = createComponent(generateTableData(12), 12);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginatorTop = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.top-paginator'}));
    const paginatorBottom = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.bottom-paginator'}));

    // Paginators start with default values, 0-9 are shown, but 10 isn't.
    expect(await paginatorTop.getPageSize()).toBe(10);
    expect(await paginatorBottom.getPageSize()).toBe(10);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
    expect(fixture.nativeElement.innerText).toContain('row0');
    expect(fixture.nativeElement.innerText).toContain('row9');
    expect(fixture.nativeElement.innerText).not.toContain('row10');
  });

  it('uses data length if it is not provided', async () => {
    const fixture = createComponent(
        generateTableData(12), undefined);  // undefined dataLength

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const paginatorTop = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.top-paginator'}));
    const paginatorBottom = await harnessLoader.getHarness(
        MatPaginatorHarness.with({selector: '.bottom-paginator'}));

    // Paginators start with default values, 0-9 are shown, but 10 isn't.
    expect(await paginatorTop.getPageSize()).toBe(10);
    expect(await paginatorBottom.getPageSize()).toBe(10);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
    expect(fixture.nativeElement.innerText).toContain('row0');
    expect(fixture.nativeElement.innerText).toContain('row9');
    expect(fixture.nativeElement.innerText).not.toContain('row10');
  });

  it('clicking TOP paginator updates bottom paginator state (page size)',
     async () => {
       const fixture = createComponent(generateTableData(55), 55);

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const paginatorTop = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.top-paginator'}));
       const paginatorBottom = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.bottom-paginator'}));

       // Change page size on top paginator should update the bottom
       await paginatorTop.setPageSize(50);
       expect(await paginatorTop.getPageSize()).toBe(50);
       expect(await paginatorBottom.getPageSize()).toBe(50);
       expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 55');
       expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 55');
       expect(fixture.nativeElement.innerText).toContain('row0');
       expect(fixture.nativeElement.innerText).toContain('row49');
     });

  it('clicking BOTTOM paginator updates top paginator state (page size)',
     async () => {
       const fixture = createComponent(generateTableData(55), 55);

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const paginatorTop = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.top-paginator'}));
       const paginatorBottom = await harnessLoader.getHarness(
           MatPaginatorHarness.with({selector: '.bottom-paginator'}));

       // Change page size on bottom paginator should update the top
       await paginatorBottom.setPageSize(50);
       expect(await paginatorTop.getPageSize()).toBe(50);
       expect(await paginatorBottom.getPageSize()).toBe(50);
       expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 55');
       expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 55');
       expect(fixture.nativeElement.innerText).toContain('row0');
       expect(fixture.nativeElement.innerText).toContain('row49');
     });

  it('shows controls when data length is updated to more than 1 page', () => {
    const fixture = createComponent(generateTableData(2), 2);

    let controlsTop = fixture.debugElement.query(By.css('.controls-top'));
    let controlsBottom = fixture.debugElement.query(By.css('.controls-bottom'));
    expect(controlsTop.nativeElement.hasAttribute('hidden')).toBeTrue();
    expect(controlsBottom.nativeElement.hasAttribute('hidden')).toBeTrue();

    fixture.componentInstance.dataLength = 50;
    fixture.detectChanges();

    controlsTop = fixture.debugElement.query(By.css('.controls-top'));
    controlsBottom = fixture.debugElement.query(By.css('.controls-bottom'));
    expect(controlsTop.nativeElement.hasAttribute('hidden')).toBeFalse();
    expect(controlsBottom.nativeElement.hasAttribute('hidden')).toBeFalse();
  });

  it('hides controls when data length is updated to less than 1 page', () => {
    const fixture = createComponent(generateTableData(10), 10);

    let controlsTop = fixture.debugElement.query(By.css('.controls-top'));
    let controlsBottom = fixture.debugElement.query(By.css('.controls-bottom'));
    expect(controlsTop.nativeElement.hasAttribute('hidden')).toBeFalse();
    expect(controlsBottom.nativeElement.hasAttribute('hidden')).toBeFalse();

    fixture.componentInstance.dataLength = 1;
    fixture.detectChanges();

    controlsTop = fixture.debugElement.query(By.css('.controls-top'));
    controlsBottom = fixture.debugElement.query(By.css('.controls-bottom'));
    expect(controlsTop.nativeElement.hasAttribute('hidden')).toBeTrue();
    expect(controlsBottom.nativeElement.hasAttribute('hidden')).toBeTrue();
  });
});
