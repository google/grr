import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {newHunt} from '../../../lib/models/model_test_util';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {FleetCollectionsStore} from '../../../store/fleet_collections_store';
import {
  FleetCollectionsStoreMock,
  FleetCollectionStoreMock,
  newFleetCollectionsStoreMock,
  newFleetCollectionStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionDebugging} from './fleet_collection_debugging';
import {FleetCollectionDebuggingHarness} from './testing/fleet_collection_debugging_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FleetCollectionDebugging);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionDebuggingHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Debugging Component', () => {
  let fleetCollectionsStoreMock: FleetCollectionsStoreMock;
  let fleetCollectionStoreMock: FleetCollectionStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionsStoreMock = newFleetCollectionsStoreMock();
    fleetCollectionStoreMock = newFleetCollectionStoreMock();

    TestBed.configureTestingModule({
      imports: [FleetCollectionDebugging, NoopAnimationsModule],
      providers: [
        {
          provide: FleetCollectionsStore,
          useValue: fleetCollectionsStoreMock,
        },
        {
          provide: FleetCollectionStore,
          useValue: fleetCollectionStoreMock,
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows fleet collection data', async () => {
    const fleetCollection = newHunt({
      huntId: 'FC1234567890',
      name: 'Test Fleet Collection',
      description: 'This is a test fleet collection',
      creator: 'testuser',
      created: new Date(1571789996681),
      flowName: 'TestFlow',
      flowArgs: {
        foo: 'bar',
      },
    });
    fleetCollectionStoreMock.fleetCollection = signal(fleetCollection);
    const {harness} = await createComponent();

    const text = await (await harness.host()).text();
    expect(text).toContain('Fleet Collection');

    expect(text).toContain('FC1234567890');
    expect(text).toContain('Test Fleet Collection');
    expect(text).toContain('This is a test fleet collection');
    expect(text).toContain('testuser');
    expect(text).toContain('2019-10-23T00:19:56.681Z');
    expect(text).toContain('TestFlow');
    expect(text).toContain('bar');
  });

  it('shows fleet collection logs', async () => {
    const {harness} = await createComponent();

    const fleetCollectionLogs = await harness.fleetCollectionLogs();
    expect(fleetCollectionLogs).toBeTruthy();
  });
});
