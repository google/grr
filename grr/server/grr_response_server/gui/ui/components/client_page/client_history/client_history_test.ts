import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {RouterModule} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {newClientSnapshot} from '../../../lib/models/model_test_util';
import {ClientStore} from '../../../store/client_store';
import {
  ClientStoreMock,
  newClientStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {ClientHistory} from './client_history';
import {ClientHistoryHarness} from './testing/client_history_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientHistory);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientHistoryHarness,
  );
  return {fixture, harness};
}

describe('Client History Component', () => {
  let clientStoreMock: ClientStoreMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();

    TestBed.configureTestingModule({
      imports: [ClientHistory, RouterModule.forRoot(CLIENT_ROUTES)],
      providers: [
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('can create empty timeline', fakeAsync(async () => {
    clientStoreMock.clientSnapshots = signal([]);
    tick();
    const {harness} = await createComponent();
    const timeline = await harness.getTimeline();

    expect(await timeline.getItems()).toHaveSize(0);
  }));

  it('displays timeline data with age as title', fakeAsync(async () => {
    clientStoreMock.clientHistory = signal([
      {
        snapshot: newClientSnapshot({
          clientId: 'C.1234',
          timestamp: new Date('2024-01-01T00:00:00Z'),
          sourceFlowId: '1234',
        }),
      },
      {
        startupInfo: {
          timestamp: new Date('2024-01-02T00:00:00Z'),
        },
      },
    ]);
    tick();

    const {harness} = await createComponent();

    const timelineItems = await harness.getTimelineItems();
    expect(timelineItems).toHaveSize(2);

    expect(await harness.getTimelineItemTitle(0)).toContain(
      '2024-01-01 00:00:00 UTC',
    );
    expect(await harness.getTimelineItemSubtitle(0)).toBeNull();

    expect(await harness.getTimelineItemTitle(1)).toContain(
      '2024-01-02 00:00:00 UTC',
    );
    expect(await harness.getTimelineItemSubtitle(1)).toBeNull();
  }));

  it('displays startup info icon for startup entries', fakeAsync(async () => {
    clientStoreMock.clientHistory = signal([
      {
        snapshot: newClientSnapshot({
          clientId: 'C.1234',
          timestamp: new Date('2024-01-01T00:00:00Z'),
          sourceFlowId: '1234',
        }),
      },
      {
        startupInfo: {
          timestamp: new Date('2024-01-02T00:00:00Z'),
        },
      },
    ]);
    const {harness} = await createComponent();

    expect(await harness.hasTimelineItemStartupInfoIcon(0)).toBeFalse();
    expect(await harness.hasTimelineItemStartupInfoIcon(1)).toBeTrue();
  }));

  it('navigation to /clients/C.1222/history/1234 opens snapshot in router outlet', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/clients/C.1222/history/1234');

    const {harness} = await createComponent();
    expect(await harness.isClientSnapshotVisible()).toBeTrue();
  }));
});
