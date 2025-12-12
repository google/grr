import {ComponentHarness} from '@angular/cdk/testing';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatTableDataSource, MatTableModule} from '@angular/material/table';
import {MatTableHarness} from '@angular/material/table/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../testing';
import {FilterPaginate} from './filter_paginate';
import {FilterPaginateHarness} from './testing/filter_paginate_harness';

initTestEnvironment();

declare interface DummyRow {
  content: string;
}

function generateRow(i: number): DummyRow {
  const content = `row${i}`;
  return {content};
}

function generateTableData(length: number) {
  const source = new MatTableDataSource<DummyRow>();
  source.data = Array.from({length}, (v, i) => generateRow(i));
  return source;
}

@Component({
  selector: 'test-component',
  template: `
<filter-paginate [dataSource]="dataSource">
  <mat-table [dataSource]="dataSource" >
    <ng-container matColumnDef="content">
      <td mat-cell *matCellDef="let r" class="cell">
        {{r.content}}
      </td>
      <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
    </ng-container>
  </mat-table>
</filter-paginate>`,
  imports: [FilterPaginate, MatTableModule],
})
class TestComponent {
  dataSource = new MatTableDataSource<DummyRow>();
  displayedColumns: string[] = ['content'];
}

/** Harness for the TestComponent component. */
export class TestComponentHarness extends ComponentHarness {
  static hostSelector = 'test-component';

  readonly table = this.locatorFor(MatTableHarness);
}

async function createComponent(dataSource: MatTableDataSource<DummyRow>) {
  const fixture = TestBed.createComponent(TestComponent);
  fixture.componentInstance.dataSource = dataSource;
  fixture.detectChanges();

  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FilterPaginateHarness,
  );

  const testComponentHarness =
    await TestbedHarnessEnvironment.harnessForFixture(
      fixture,
      TestComponentHarness,
    );
  return {fixture, harness, testComponentHarness};
}

describe('FilterPaginate Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, TestComponent],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent(generateTableData(10));

    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows control ', async () => {
    const {harness} = await createComponent(generateTableData(11));

    const paginatorTop = await harness.paginatorTop();
    await paginatorTop.setPageSize(10);

    expect(await harness.filterInput()).toBeDefined();
    expect(await harness.paginatorTop()).toBeDefined();
    expect(await harness.paginatorBottom()).toBeDefined();
  });

  it('initially does not filter results', async () => {
    const {harness, testComponentHarness} = await createComponent(
      generateTableData(10),
    );

    const filterInput = await harness.filterInput();
    expect(await filterInput.getValue()).toBe('');
    const table = await testComponentHarness.table();
    const rows = await table.getRows();
    expect(rows.length).toBe(10);
    expect(await rows[0].getCellTextByColumnName()).toEqual({
      'content': 'row0',
    });
    expect(await rows[9].getCellTextByColumnName()).toEqual({
      'content': 'row9',
    });
  });

  it('filters results', async () => {
    const {harness, testComponentHarness} = await createComponent(
      generateTableData(10),
    );

    const filterInput = await harness.filterInput();
    await filterInput.setValue('row0');

    const table = await testComponentHarness.table();
    const rows = await table.getRows();
    expect(rows.length).toBe(1);
    expect(await rows[0].getCellTextByColumnName()).toEqual({
      'content': 'row0',
    });
  });

  it('default pagination works', async () => {
    const {harness, testComponentHarness} = await createComponent(
      generateTableData(12),
    );

    const paginatorTop = await harness.paginatorTop();
    expect(await paginatorTop.getPageSize()).toBe(10);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 10 of 12');
    const paginatorBottom = await harness.paginatorBottom();
    expect(await paginatorBottom.getPageSize()).toBe(10);
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 10 of 12');
    const table = await testComponentHarness.table();
    const rows = await table.getRows();
    expect(rows.length).toBe(10);
    expect(await rows[0].getCellTextByColumnName()).toEqual({
      'content': 'row0',
    });
    expect(await rows[9].getCellTextByColumnName()).toEqual({
      'content': 'row9',
    });
  });

  it('clicking top paginator updates bottom paginator state (page size)', fakeAsync(async () => {
    const {harness} = await createComponent(generateTableData(55));

    const paginatorTop = await harness.paginatorTop();
    await paginatorTop.setPageSize(50);

    tick();

    // Change page size on top paginator should update the bottom
    const paginatorBottom = await harness.paginatorBottom();
    expect(await paginatorBottom.getPageSize()).toBe(50);
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 55');
    expect(await paginatorTop.getPageSize()).toBe(50);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 55');
  }));

  it('clicking bottom paginator updates top paginator state (page size)', fakeAsync(async () => {
    const {harness} = await createComponent(generateTableData(55));

    const paginatorBottom = await harness.paginatorBottom();
    await paginatorBottom.setPageSize(50);

    tick();

    // Change page size on bottom paginator should update the top
    const paginatorTop = await harness.paginatorTop();
    expect(await paginatorTop.getPageSize()).toBe(50);
    expect(await paginatorTop.getRangeLabel()).toBe('1 – 50 of 55');
    expect(await paginatorBottom.getPageSize()).toBe(50);
    expect(await paginatorBottom.getRangeLabel()).toBe('1 – 50 of 55');
  }));
});
