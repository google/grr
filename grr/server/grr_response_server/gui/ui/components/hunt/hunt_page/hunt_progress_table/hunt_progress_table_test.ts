import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {HuntCompletionProgressTableRow} from '../../../../lib/models/hunt';
import {initTestEnvironment} from '../../../../testing';

import {HuntProgressTable} from './hunt_progress_table';

initTestEnvironment();

@Component({
  template: `<app-hunt-progress-table
    [completionProgressData]="completionProgressData"
    [totalClients]="totalClients">
  </app-hunt-progress-table>`,
})
class TestHostComponent {
  completionProgressData: HuntCompletionProgressTableRow[] | null = null;
  totalClients: bigint | null | undefined = null;
}

describe('HuntProgressTable Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HuntProgressTable],
      declarations: [TestHostComponent],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('shows a message if table data is null', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.detectChanges();

    const table = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-table',
    );

    expect(table).toBeNull();

    const noDataBlock = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container .no-data',
    );

    expect(noDataBlock).not.toBeNull();
    expect(noDataBlock.textContent).toEqual(
      'There is no hunt progress data to show.',
    );
  });

  it('shows a message if table data is empty', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.completionProgressData = [];

    fixture.detectChanges();

    const table = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-table',
    );

    expect(table).toBeNull();

    const noDataBlock = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container .no-data',
    );

    expect(noDataBlock).not.toBeNull();
    expect(noDataBlock.textContent).toEqual(
      'There is no hunt progress data to show.',
    );
  });

  it('shows a table with 3 rows', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.completionProgressData = [
      {
        timestamp: 0,
        scheduledClients: BigInt(10),
        completedClients: BigInt(0),
      },
      {
        timestamp: 10,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
      },
      {
        timestamp: 20,
        scheduledClients: BigInt(10),
        completedClients: BigInt(10),
      },
    ];

    fixture.detectChanges();

    const table = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-table',
    );

    expect(table).not.toBeNull();

    const tableRows = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row',
    );

    expect(tableRows.length).toEqual(3);
  });

  it('shows a table with the specified raw numbers', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.completionProgressData = [
      {
        timestamp: 1678379900000,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
      },
    ];

    fixture.detectChanges();

    const table = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-table',
    );

    expect(table).not.toBeNull();

    const tableRows = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row',
    );

    expect(tableRows.length).toEqual(1);

    const timestampCell = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-row app-timestamp .contents',
    );

    expect(timestampCell).not.toBeNull();
    expect(timestampCell.textContent).toEqual('2023-03-09 16:38:20 UTC');

    const clientCells = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row .hunt-progress-cell',
    );

    expect(clientCells.length).toBe(2);

    const completedClientsCell = clientCells[0];
    const scheduledClientsCell = clientCells[1];

    expect(completedClientsCell).not.toBeNull();
    expect(scheduledClientsCell).not.toBeNull();

    expect(completedClientsCell.textContent).toEqual('5');
    expect(scheduledClientsCell.textContent).toEqual('10');
  });

  it('shows a table with the specified raw numbers and percentages', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.completionProgressData = [
      {
        timestamp: 1678379900000,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
        scheduledClientsPct: BigInt(100),
        completedClientsPct: BigInt(50),
      },
    ];

    hostComponentInstance.totalClients = BigInt(10);

    fixture.detectChanges();

    const table = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-table',
    );

    expect(table).not.toBeNull();

    const tableRows = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row',
    );

    expect(tableRows.length).toEqual(1);

    const timestampCell = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-row app-timestamp .contents',
    );
    expect(timestampCell).not.toBeNull();

    expect(timestampCell.textContent).toEqual('2023-03-09 16:38:20 UTC');

    const clientCells = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row .hunt-progress-cell',
    );

    expect(clientCells.length).toBe(2);

    const completedClientsCell = clientCells[0];

    expect(completedClientsCell).not.toBeNull();
    expect(completedClientsCell.textContent.trim()).toEqual('5 (50%)');

    const scheduledClientsCell = clientCells[1];

    expect(scheduledClientsCell).not.toBeNull();
    expect(scheduledClientsCell.textContent.trim()).toEqual('10 (100%)');
  });

  it('reacts to changes in the table data', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.completionProgressData = [
      {
        timestamp: 0,
        scheduledClients: BigInt(10),
        completedClients: BigInt(0),
      },
      {
        timestamp: 10,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
      },
    ];

    fixture.detectChanges();

    const table = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-table',
    );

    expect(table).not.toBeNull();

    let tableRows = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row',
    );

    expect(tableRows.length).toEqual(2);

    hostComponentInstance.completionProgressData = [
      {
        timestamp: 0,
        scheduledClients: BigInt(10),
        completedClients: BigInt(0),
      },
    ];

    fixture.detectChanges();

    tableRows = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row',
    );

    expect(tableRows.length).toEqual(1);
  });

  it('caps the height of the table to 400px', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    const hostComponentInstance = fixture.componentInstance;

    hostComponentInstance.completionProgressData = [
      {
        timestamp: 0,
        scheduledClients: BigInt(10),
        completedClients: BigInt(0),
      },
      {
        timestamp: 10,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
      },
      {
        timestamp: 20,
        scheduledClients: BigInt(10),
        completedClients: BigInt(10),
      },
      {
        timestamp: 0,
        scheduledClients: BigInt(10),
        completedClients: BigInt(0),
      },
      {
        timestamp: 10,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
      },
      {
        timestamp: 20,
        scheduledClients: BigInt(10),
        completedClients: BigInt(10),
      },
      {
        timestamp: 0,
        scheduledClients: BigInt(10),
        completedClients: BigInt(0),
      },
      {
        timestamp: 10,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
      },
      {
        timestamp: 20,
        scheduledClients: BigInt(10),
        completedClients: BigInt(10),
      },
      {
        timestamp: 0,
        scheduledClients: BigInt(10),
        completedClients: BigInt(0),
      },
      {
        timestamp: 10,
        scheduledClients: BigInt(10),
        completedClients: BigInt(5),
      },
      {
        timestamp: 20,
        scheduledClients: BigInt(10),
        completedClients: BigInt(10),
      },
    ];

    fixture.detectChanges();

    const table = fixture.nativeElement.querySelector(
      '.hunt-progress-table-container mat-table',
    );

    expect(table).not.toBeNull();

    const tableRows = fixture.nativeElement.querySelectorAll(
      '.hunt-progress-table-container mat-table mat-row',
    );

    expect(tableRows.length).toEqual(12);

    expect(table.getBoundingClientRect().height).toEqual(400);
  });
});
