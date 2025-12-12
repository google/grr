import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {RouterModule} from '@angular/router';

import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';
import {ClientSnapshot} from '../../../lib/models/client';
import {newClientSnapshot} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';
import {
  SnapshotEntryHistoryDialog,
  SnapshotEntryHistoryDialogData,
} from './snapshot_entry_history_dialog';
import {SnapshotEntryHistoryDialogHarness} from './testing/snapshot_entry_history_dialog_harness';

initTestEnvironment();

async function createDialog(dialogData: SnapshotEntryHistoryDialogData) {
  const opener = MatTestDialogOpener.withComponent<
    SnapshotEntryHistoryDialog,
    SnapshotEntryHistoryDialogData
  >(SnapshotEntryHistoryDialog, {data: dialogData});

  const fixture = TestBed.createComponent(opener);
  fixture.detectChanges();
  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(
    SnapshotEntryHistoryDialogHarness,
  );
  return {fixture, dialogHarness};
}

describe('Snapshot Entry History Dialog', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      declarations: [],
      imports: [
        SnapshotEntryHistoryDialog,
        MatTestDialogOpenerModule,
        RouterModule.forRoot([]),
      ],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            snapshots: [],
            entryAccessor: (client: ClientSnapshot) => client.clientId ?? '',
          },
        },
      ],
    }).compileComponents();
  }));

  it('shows the table with the history entries', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      snapshots: [
        newClientSnapshot({
          clientId: 'C.1234',
          sourceFlowId: '1234',
          timestamp: new Date('2024-01-01T00:00:00Z'),
        }),
        newClientSnapshot({
          clientId: 'C.1234',
          sourceFlowId: '2345',
          timestamp: new Date('2023-01-01T00:00:00Z'),
        }),
        newClientSnapshot({
          clientId: 'C.1234',
          sourceFlowId: '3456',
          timestamp: new Date('2022-01-01T00:00:00Z'),
        }),
      ],
      entryAccessor: (client: ClientSnapshot) => client.sourceFlowId ?? '',
    });

    const table = await dialogHarness.table();
    const rows = await table.getRows();

    expect(rows).toHaveSize(3);
    expect(await rows[0].getCellTextByColumnName()).toEqual({
      timestamp: '2024-01-01 00:00:00 UTC content_copy',
      value: '1234',
    });
    expect(await rows[1].getCellTextByColumnName()).toEqual({
      timestamp: '2023-01-01 00:00:00 UTC content_copy',
      value: '2345',
    });
    expect(await rows[2].getCellTextByColumnName()).toEqual({
      timestamp: '2022-01-01 00:00:00 UTC content_copy',
      value: '3456',
    });
  }));
});
