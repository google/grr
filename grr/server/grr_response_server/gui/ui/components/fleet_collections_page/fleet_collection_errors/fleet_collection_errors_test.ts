import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {newHuntError} from '../../../lib/models/model_test_util';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {
  FleetCollectionStoreMock,
  newFleetCollectionStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionErrors} from './fleet_collection_errors';
import {FleetCollectionErrorsHarness} from './testing/fleet_collection_errors_harness';

initTestEnvironment();

async function createComponent(fleetCollectionId = '1234') {
  const fixture = TestBed.createComponent(FleetCollectionErrors);
  fixture.componentRef.setInput('fleetCollectionId', fleetCollectionId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionErrorsHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Errors Component', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();

    TestBed.configureTestingModule({
      imports: [FleetCollectionErrors, NoopAnimationsModule],
      providers: [
        {
          provide: FleetCollectionStore,
          useValue: fleetCollectionStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    }).compileComponents();
  }));

  it('is created', fakeAsync(async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  }));

  it('shows correct number of results loaded', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionErrors = signal([
      newHuntError({}),
      newHuntError({}),
    ]);
    fleetCollectionStoreMock.totalErrorsCount = signal(3);

    const {harness} = await createComponent();

    expect(await harness.loadedErrorsText()).toContain('2 of 3 errors loaded');
  }));

  it('shows `Load more` button if there are more results to load', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionErrors = signal([
      newHuntError({}),
      newHuntError({}),
    ]);
    fleetCollectionStoreMock.totalErrorsCount = signal(3);

    const {harness} = await createComponent();

    expect(await harness.hasLoadMoreButton()).toBeTrue();
  }));

  it('does not show `Load more` button if there are no more results to load', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionErrors = signal([
      newHuntError({}),
      newHuntError({}),
    ]);
    fleetCollectionStoreMock.totalErrorsCount = signal(2);

    const {harness} = await createComponent();

    expect(await harness.hasLoadMoreButton()).toBeFalse();
  }));

  it('shows errors table', fakeAsync(async () => {
    fleetCollectionStoreMock.fleetCollectionErrors = signal([
      newHuntError({
        clientId: 'C.1234',
        logMessage: 'fooLog',
        backtrace: 'fooTrace',
        timestamp: new Date(1677685622200),
      }),
      newHuntError({
        clientId: 'C.5678',
        logMessage: 'barLog \n secondLine',
        backtrace: 'barTrace \n secondLine',
        timestamp: new Date(1677685611100),
      }),
    ]);

    const {harness} = await createComponent();

    const table = await harness.table();
    expect(await table.getRows()).toHaveSize(2);
    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
    expect(await harness.getCellText(0, 'logMessage')).toContain('fooLog');
    expect(await harness.getCellText(0, 'backtrace')).toContain('fooTrace');
    expect(await harness.getCellText(0, 'timestamp')).toContain(
      '2023-03-01 15:47:02 UTC',
    );
    expect(await harness.getCellText(1, 'clientId')).toContain('C.5678');
    expect(await harness.getCellText(1, 'logMessage')).toContain('barLog');
    expect(await harness.getCellText(1, 'logMessage')).toContain('secondLine');
    expect(await harness.getCellText(1, 'backtrace')).toContain('barTrace');
    expect(await harness.getCellText(1, 'backtrace')).toContain('secondLine');
    expect(await harness.getCellText(1, 'timestamp')).toContain(
      '2023-03-01 15:46:51 UTC',
    );
  }));
});
