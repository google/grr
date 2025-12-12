import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

import {HttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_test_util';
import {newHuntApproval} from '../../lib/models/model_test_util';
import {FleetCollectionStore} from '../../store/fleet_collection_store';
import {FleetCollectionsStore} from '../../store/fleet_collections_store';
import {
  FleetCollectionStoreMock,
  newFleetCollectionsStoreMock,
  newFleetCollectionStoreMock,
} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {FLEET_COLLECTION_ROUTES} from '../app/routing';
import {FleetCollectionDetails} from './fleet_collection_details';
import {FleetCollectionDetailsHarness} from './testing/fleet_collection_details_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FleetCollectionDetails);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionDetailsHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Details Component', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();

    TestBed.configureTestingModule({
      imports: [
        FleetCollectionDetails,
        NoopAnimationsModule,
        RouterModule.forRoot(FLEET_COLLECTION_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: FleetCollectionsStore,
          useValue: newFleetCollectionsStoreMock(),
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    })
      .overrideComponent(FleetCollectionDetails, {
        set: {
          providers: [
            {
              provide: FleetCollectionStore,
              useValue: fleetCollectionStoreMock,
            },
          ],
        },
      })
      .compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('calls polling methods on the store when navigating to the page', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/fleet-collections/1234');

    expect(fleetCollectionStoreMock.pollFleetCollection).toHaveBeenCalled();
    expect(
      fleetCollectionStoreMock.pollFleetCollectionApprovals,
    ).toHaveBeenCalled();
    expect(fleetCollectionStoreMock.pollUntilAccess).toHaveBeenCalled();
  }));

  it('has tabs', async () => {
    const {harness} = await createComponent();

    const tabs = await harness.tabs();
    expect(tabs).toHaveSize(5);
    expect(await tabs[0].getLabel()).toBe('CONFIGURATION');
    expect(await tabs[1].getLabel()).toBe('RESULTS');
    expect(await tabs[2].getLabel()).toBe('ERRORS');
    expect(await tabs[3].getLabel()).toBe('DEBUGGING');
    expect(await tabs[4].getLabel()).toContain('APPROVALS');
  });

  it('navigation to /results opens FleetCollectionResults component', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/fleet-collections/1234/results');

    const {harness} = await createComponent();
    expect(await harness.hasResultsComponent()).toBeTrue();
  }));

  it('navigation to /configuration opens FleetCollectionConfiguration component', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl(
      '/fleet-collections/1234/configuration',
    );

    const {harness} = await createComponent();
    expect(await harness.hasConfigurationComponent()).toBeTrue();
  }));

  it('navigation to /debug opens FleetCollectionDebugging component', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/fleet-collections/1234/debug');

    const {harness} = await createComponent();
    expect(await harness.hasDebuggingComponent()).toBeTrue();
  }));

  it('navigation to /approvals opens FleetCollectionApprovals component', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl(
      '/fleet-collections/1234/approvals',
    );

    const {harness} = await createComponent();
    expect(await harness.hasApprovalsComponent()).toBeTrue();
  }));

  it('opens results tab by default', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/fleet-collections/1234');

    const {harness} = await createComponent();
    expect(await harness.hasResultsComponent()).toBeTrue();
  }));

  it('shows approval chip if user got approval', fakeAsync(async () => {
    fleetCollectionStoreMock.latestApproval = signal(
      newHuntApproval({
        huntId: '1234',
        status: {type: 'valid'},
      }),
    );
    const {harness} = await createComponent();

    const approvalChip = await harness.approvalChip();
    expect(approvalChip).toBeTruthy();
    expect(await approvalChip!.isAccessGrantedChipVisible()).toBeTrue();
  }));

  it('shows approval chip if user has no access', fakeAsync(async () => {
    fleetCollectionStoreMock.hasAccess = signal(false);
    const {harness} = await createComponent();

    const approvalChip = await harness.approvalChip();
    expect(approvalChip).toBeTruthy();
    expect(await approvalChip!.isAccessDeniedChipVisible()).toBeTrue();
  }));

  it('shows no approval chip if access is granted without approval (e.g. disabled approvals)', fakeAsync(async () => {
    fleetCollectionStoreMock.hasAccess = signal(true);
    fleetCollectionStoreMock.latestApproval = signal(null);

    const {harness} = await createComponent();

    const approvalChip = await harness.approvalChip();
    expect(approvalChip).toBeNull();
  }));
});
