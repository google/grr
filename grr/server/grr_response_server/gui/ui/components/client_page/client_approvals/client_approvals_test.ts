import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {RouterModule} from '@angular/router';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {
  newClient,
  newClientApproval,
  newGrrUser,
} from '../../../lib/models/model_test_util';
import {ApprovalRequestStore} from '../../../store/approval_request_store';
import {ClientStore} from '../../../store/client_store';
import {GlobalStore} from '../../../store/global_store';
import {
  ApprovalRequestStoreMock,
  ClientStoreMock,
  GlobalStoreMock,
  newApprovalRequestStoreMock,
  newClientStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {ClientApprovals} from './client_approvals';
import {ClientApprovalsHarness} from './testing/client_approvals_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientApprovals);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientApprovalsHarness,
  );

  return {fixture, harness};
}

describe('Client Approvals Component', () => {
  let clientStoreMock: ClientStoreMock;
  let approvalRequestStoreMock: ApprovalRequestStoreMock;
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();
    approvalRequestStoreMock = newApprovalRequestStoreMock();
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        ClientApprovals,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
          paramsInheritanceStrategy: 'always',
        }),
      ],
      providers: [
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: ApprovalRequestStore,
          useValue: approvalRequestStoreMock,
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness} = await createComponent();
    expect(harness).toBeDefined();
  });

  it('shows approval form when no approval and no access', async () => {
    clientStoreMock.hasAccess = signal(false);
    clientStoreMock.latestApproval = signal(null);
    const {harness} = await createComponent();

    expect(await harness.isApprovalFormVisible()).toBeTrue();
    expect(await harness.isPendingApprovalVisible()).toBeFalse();
    expect(await harness.isGrantedApprovalVisible()).toBeFalse();
  });

  it('shows pending approval when there is a pending approval', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(false);
    const pendingApproval = newClientApproval({
      status: {type: 'pending', reason: 'Need 1 more approver'},
    });
    clientStoreMock.latestApproval = signal(pendingApproval);
    clientStoreMock.clientApprovals = signal([pendingApproval]);
    tick();
    const {harness} = await createComponent();

    expect(await harness.isApprovalFormVisible()).toBeFalse();
    expect(await harness.isPendingApprovalVisible()).toBeTrue();
    expect(await harness.isGrantedApprovalVisible()).toBeFalse();
  }));

  it('shows all pending approvals when the latest approval is pending', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(false);
    const latestApproval = newClientApproval({
      status: {type: 'pending', reason: 'Need 1 more approver'},
    });
    clientStoreMock.latestApproval = signal(latestApproval);
    clientStoreMock.clientApprovals = signal([
      latestApproval,
      newClientApproval({
        status: {type: 'expired', reason: 'Need 1 more approver'},
      }),
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    ]);
    const {harness} = await createComponent();

    expect(await harness.numberOfPendingApprovals()).toBe(2);
  }));

  it('shows granted approval when there is a granted approval', async () => {
    clientStoreMock.hasAccess = signal(true);
    clientStoreMock.latestApproval = signal(
      newClientApproval({
        status: {type: 'valid'},
      }),
    );
    const {harness} = await createComponent();

    expect(await harness.isApprovalFormVisible()).toBeFalse();
    expect(await harness.isPendingApprovalVisible()).toBeFalse();
    expect(await harness.isGrantedApprovalVisible()).toBeTrue();
  });

  it('shows approval form button when there is a pending approval', async () => {
    clientStoreMock.hasAccess = signal(true);
    clientStoreMock.latestApproval = signal(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    const {harness} = await createComponent();

    expect(await harness.isShowApprovalFormButtonVisible()).toBeTrue();
  });

  it('shows approval form when clicking on the approval form button', async () => {
    clientStoreMock.hasAccess = signal(true);
    clientStoreMock.latestApproval = signal(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    const {harness} = await createComponent();

    expect(await harness.isShowApprovalFormButtonVisible()).toBeTrue();
    await harness.clickShowApprovalFormButton();

    expect(await harness.isApprovalFormVisible()).toBeTrue();
  });

  it('does not show approval request when there is no requested approval', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    approvalRequestStoreMock.requestedClientApproval = signal(null);
    const {harness} = await createComponent();
    expect(await harness.isApprovalRequestVisible()).toBeFalse();
  }));

  it('shows approval request when there is a requested approval for the current client', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    approvalRequestStoreMock.requestedClientApproval = signal(
      newClientApproval({
        subject: newClient({clientId: 'C.1234'}),
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    const {harness} = await createComponent();

    expect(await harness.isApprovalRequestVisible()).toBeTrue();
  }));
  it('does not show approval request when there is a requested approval for a different client', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    approvalRequestStoreMock.requestedClientApproval = signal(
      newClientApproval({
        subject: newClient({clientId: 'C.4321'}),
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    const {harness} = await createComponent();
    expect(await harness.isApprovalRequestVisible()).toBeFalse();
  }));

  it('does not show approval request when there is no requested approval', fakeAsync(async () => {
    approvalRequestStoreMock.requestedClientApproval = signal(null);
    const {harness} = await createComponent();
    expect(await harness.isApprovalRequestVisible()).toBeFalse();
  }));

  it('does not show approval request when there is a requested approval for a different client', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1111');
    approvalRequestStoreMock.requestedClientApproval = signal(
      newClientApproval({
        subject: newClient({clientId: 'C.2222'}),
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    const {harness} = await createComponent();
    expect(await harness.isApprovalRequestVisible()).toBeFalse();
  }));

  it('calls store to grant approval on button click', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    globalStoreMock.currentUser = signal(newGrrUser({name: 'new_approver'}));
    approvalRequestStoreMock.requestedClientApproval = signal(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
        approvers: ['approver1'],
        requestor: 'requestor',
        subject: newClient({clientId: 'C.1234'}),
      }),
    );
    const {harness} = await createComponent();

    const approvalRequest = await harness.approvalRequest();

    const grantApprovalButton = await approvalRequest!.getGrantApprovalButton();
    await grantApprovalButton.click();
    expect(approvalRequestStoreMock.grantClientApproval).toHaveBeenCalled();
  }));
});
