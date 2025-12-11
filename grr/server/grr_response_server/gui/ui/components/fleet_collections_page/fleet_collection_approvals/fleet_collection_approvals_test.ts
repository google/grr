import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {
  newGrrUser,
  newHunt,
  newHuntApproval,
} from '../../../lib/models/model_test_util';
import {ApprovalRequestStore} from '../../../store/approval_request_store';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {FleetCollectionsStore} from '../../../store/fleet_collections_store';
import {GlobalStore} from '../../../store/global_store';
import {
  ApprovalRequestStoreMock,
  FleetCollectionStoreMock,
  GlobalStoreMock,
  newApprovalRequestStoreMock,
  newFleetCollectionsStoreMock,
  newFleetCollectionStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionApprovals} from './fleet_collection_approvals';
import {FleetCollectionApprovalsHarness} from './testing/fleet_collection_approvals_harness';

initTestEnvironment();

async function createComponent(fleetCollectionId = '1234') {
  const fixture = TestBed.createComponent(FleetCollectionApprovals);
  fixture.componentRef.setInput('fleetCollectionId', fleetCollectionId);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionApprovalsHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collection Approvals Component', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;
  let globalStoreMock: GlobalStoreMock;
  let approvalRequestStoreMock: ApprovalRequestStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();
    globalStoreMock = newGlobalStoreMock();
    approvalRequestStoreMock = newApprovalRequestStoreMock();

    TestBed.configureTestingModule({
      imports: [
        FleetCollectionApprovals,
        NoopAnimationsModule,
        RouterModule.forRoot([], {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
        {
          provide: ApprovalRequestStore,
          useValue: approvalRequestStoreMock,
        },
        {
          provide: FleetCollectionsStore,
          useValue: newFleetCollectionsStoreMock(),
        },
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

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('shows approval form when no approval and no access', async () => {
    fleetCollectionStoreMock.hasAccess = signal(false);
    fleetCollectionStoreMock.latestApproval = signal(null);
    const {harness} = await createComponent();

    expect(await harness.isApprovalFormVisible()).toBeTrue();
  });

  it('shows pending approval when there is a pending approval', fakeAsync(async () => {
    fleetCollectionStoreMock.hasAccess = signal(false);
    const pendingApproval = newHuntApproval({
      status: {type: 'pending', reason: 'Need 1 more approver'},
    });
    fleetCollectionStoreMock.latestApproval = signal(pendingApproval);
    fleetCollectionStoreMock.fleetCollectionApprovals = signal([
      pendingApproval,
    ]);
    const {harness} = await createComponent();

    expect(await harness.isPendingApprovalVisible()).toBeTrue();
  }));

  it('shows all pending approvals when the latest approval is pending', fakeAsync(async () => {
    fleetCollectionStoreMock.hasAccess = signal(false);
    const latestApproval = newHuntApproval({
      status: {type: 'pending', reason: 'Need 1 more approver'},
    });
    fleetCollectionStoreMock.latestApproval = signal(latestApproval);
    fleetCollectionStoreMock.fleetCollectionApprovals = signal([
      latestApproval,
      newHuntApproval({
        status: {type: 'expired', reason: 'Need 1 more approver'},
      }),
      newHuntApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    ]);
    const {harness} = await createComponent();

    expect(await harness.numberOfPendingApprovals()).toBe(2);
  }));

  it('shows granted approval when there is a granted approval', async () => {
    fleetCollectionStoreMock.hasAccess = signal(true);
    fleetCollectionStoreMock.latestApproval = signal(
      newHuntApproval({
        status: {type: 'valid'},
      }),
    );
    const {harness} = await createComponent();

    expect(await harness.isGrantedApprovalVisible()).toBeTrue();
  });

  it('shows approval form button when there is a pending approval', async () => {
    fleetCollectionStoreMock.hasAccess = signal(true);
    fleetCollectionStoreMock.latestApproval = signal(
      newHuntApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    const {harness} = await createComponent();

    expect(await harness.isShowApprovalFormButtonVisible()).toBeTrue();
  });

  it('shows approval form when clicking on the approval form button', async () => {
    fleetCollectionStoreMock.hasAccess = signal(true);
    fleetCollectionStoreMock.latestApproval = signal(
      newHuntApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    const {harness} = await createComponent();

    expect(await harness.isShowApprovalFormButtonVisible()).toBeTrue();
    await harness.clickShowApprovalFormButton();

    expect(await harness.isApprovalFormVisible()).toBeTrue();
  });

  it('does not show approval request when there is no requested approval', fakeAsync(async () => {
    approvalRequestStoreMock.requestedFleetCollectionApproval = signal(null);
    const {harness} = await createComponent();
    expect(await harness.isApprovalRequestVisible()).toBeFalse();
  }));

  it('does not show approval request when there is a requested approval for a different fleet collection', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(newGrrUser({name: 'new_approver'}));
    approvalRequestStoreMock.requestedFleetCollectionApproval = signal(
      newHuntApproval({
        approvers: ['approver1'],
        requestor: 'requestor',
        status: {type: 'pending', reason: 'Need 1 more approver'},
        subject: newHunt({huntId: 'AAAAAAAA'}),
      }),
    );
    const {harness} = await createComponent('BBBBBBBB');

    expect(await harness.approvalRequest()).toBeNull();
  }));

  it('calls store to grant approval on button click', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(newGrrUser({name: 'new_approver'}));
    approvalRequestStoreMock.requestedFleetCollectionApproval = signal(
      newHuntApproval({
        approvers: ['approver1'],
        requestor: 'requestor',
        status: {type: 'pending', reason: 'Need 1 more approver'},
        subject: newHunt({huntId: 'ABCD1234'}),
      }),
    );
    const {harness} = await createComponent('ABCD1234');

    const approvalRequest = await harness.approvalRequest();
    const grantApprovalButton = await approvalRequest!.getGrantApprovalButton();
    await grantApprovalButton.click();
    expect(
      approvalRequestStoreMock.grantFleetCollectionApproval,
    ).toHaveBeenCalled();
  }));
});
