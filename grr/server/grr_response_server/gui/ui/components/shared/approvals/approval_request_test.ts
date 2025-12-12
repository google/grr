import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {
  newClient,
  newClientApproval,
  newGrrUser,
  newHunt,
  newHuntApproval,
} from '../../../lib/models/model_test_util';
import {Approval} from '../../../lib/models/user';
import {ApprovalRequestStore} from '../../../store/approval_request_store';
import {GlobalStore} from '../../../store/global_store';
import {
  ApprovalRequestStoreMock,
  GlobalStoreMock,
  newApprovalRequestStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ApprovalRequest} from './approval_request';
import {ApprovalRequestHarness} from './testing/approval_request_harness';

initTestEnvironment();

async function createComponent(approval: Approval) {
  const fixture = TestBed.createComponent(ApprovalRequest);
  fixture.componentRef.setInput('approval', approval);
  fixture.detectChanges();

  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ApprovalRequestHarness,
  );
  return {fixture, harness};
}

describe('Approval Request Component', () => {
  let approvalRequestStoreMock: ApprovalRequestStoreMock;
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    approvalRequestStoreMock = newApprovalRequestStoreMock();
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [
        ApprovalRequest,
        NoopAnimationsModule,
        RouterModule.forRoot([]),
      ],
      providers: [
        {
          provide: ApprovalRequestStore,
          useValue: approvalRequestStoreMock,
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', fakeAsync(async () => {
    const {fixture} = await createComponent(newClientApproval({}));

    expect(fixture.componentInstance).toBeTruthy();
  }));

  it('shows approval card with grant approval button if there is an approval', fakeAsync(async () => {
    const {harness} = await createComponent(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );

    const approvalCard = await harness.approvalCard();
    expect(approvalCard).toBeDefined();
    expect(await harness.getGrantApprovalButton()).toBeDefined();
  }));

  it('shows all approval information for a client approval', fakeAsync(async () => {
    const {harness} = await createComponent(
      newClientApproval({
        approvers: ['approver1', 'approver2'],
        expirationTime: new Date('2020-07-01T13:00:00.000+00:00'),
        reason: 'test reason',
        requestedApprovers: ['requestedApprover1', 'requestedApprover2'],
        requestor: 'testuser',
        status: {type: 'pending', reason: 'Need 1 more approver'},
        subject: newClient({
          clientId: 'C.1234',
          knowledgeBase: {
            fqdn: 'test.example.com',
          },
        }),
      }),
    );

    const approvalCard = await harness.approvalCard();
    expect(approvalCard).toBeDefined();
    expect(await approvalCard!.getTitleText()).toContain('Approval request');

    expect(await approvalCard!.getText()).toContain('Requested by:');
    expect(await approvalCard!.getText()).toContain('testuser');

    expect(await approvalCard!.getText()).toContain('Sent to:');
    expect(await approvalCard!.getText()).toContain('requestedApprover1');
    expect(await approvalCard!.getText()).toContain('requestedApprover2');

    expect(await approvalCard!.getText()).toContain('Reason:');
    expect(await approvalCard!.getText()).toContain('test reason');

    expect(await approvalCard!.getText()).toContain('Client:');
    expect(await approvalCard!.getText()).toContain(
      'test.example.com (C.1234)',
    );

    expect(await approvalCard!.getText()).toContain('Expiration:');
    expect(await approvalCard!.getText()).toContain('2020-07-01 13:00:00 UTC');

    expect(await approvalCard!.getText()).toContain('Status:');
    expect(await approvalCard!.getText()).toContain('pending');

    expect(await approvalCard!.getText()).toContain('Granted by:');
    expect(await approvalCard!.getText()).toContain('approver1');
    expect(await approvalCard!.getText()).toContain('approver2');
  }));

  it('shows all approval information for a fleet collection approval', fakeAsync(async () => {
    const {harness} = await createComponent(
      newHuntApproval({
        approvers: ['approver1', 'approver2'],
        expirationTime: new Date('2020-07-01T13:00:00.000+00:00'),
        reason: 'test reason',
        requestedApprovers: ['requestedApprover1', 'requestedApprover2'],
        requestor: 'testuser',
        status: {type: 'pending', reason: 'Need 1 more approver'},
        subject: newHunt({
          huntId: 'ABCD1234',
          flowReference: {
            clientId: 'C.1234567890',
            flowId: 'ABCDEF',
          },
        }),
      }),
    );

    const approvalCard = await harness.approvalCard();
    expect(approvalCard).toBeDefined();
    expect(await approvalCard!.getTitleText()).toContain('Approval request');

    expect(await approvalCard!.getText()).toContain('Requested by:');
    expect(await approvalCard!.getText()).toContain('testuser');

    expect(await approvalCard!.getText()).toContain('Sent to:');
    expect(await approvalCard!.getText()).toContain('requestedApprover1');
    expect(await approvalCard!.getText()).toContain('requestedApprover2');

    expect(await approvalCard!.getText()).toContain('Reason:');
    expect(await approvalCard!.getText()).toContain('test reason');

    expect(await approvalCard!.getText()).toContain('Fleet collection:');
    expect(await approvalCard!.getText()).toContain('ABCD1234');

    expect(await approvalCard!.getText()).toContain('Source Flow:');
    expect(await approvalCard!.getText()).toContain('ABCDEF on C.1234567890');

    expect(await approvalCard!.getText()).toContain('Status:');
    expect(await approvalCard!.getText()).toContain('pending');

    expect(await approvalCard!.getText()).toContain('Granted by:');
    expect(await approvalCard!.getText()).toContain('approver1');
    expect(await approvalCard!.getText()).toContain('approver2');
  }));

  it('shows source fleet collection if fleet collection reference is set', fakeAsync(async () => {
    const {harness} = await createComponent(
      newHuntApproval({
        subject: newHunt({
          huntId: 'ABCD1234',
          huntReference: {
            huntId: 'EFGH5678',
          },
        }),
      }),
    );
    const approvalCard = await harness.approvalCard();

    expect(approvalCard).toBeDefined();
    expect(await approvalCard!.getText()).toContain('Source Fleet Collection:');
    expect(await approvalCard!.getText()).toContain('EFGH5678');
    expect(await approvalCard!.getText()).not.toContain('Source Flow:');
  }));

  it('shows enabled grant approval button if the current user can approve', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(newGrrUser({name: 'new_approver'}));
    const {harness} = await createComponent(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
        approvers: ['approver1'],
        requestor: 'requestor',
      }),
    );

    const grantApprovalButton = await harness.getGrantApprovalButton();
    expect(await grantApprovalButton.isDisabled()).toBeFalse();
  }));

  it('shows disabled grant approval button if the current user is not set', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(null);
    const {harness} = await createComponent(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );

    const grantApprovalButton = await harness.getGrantApprovalButton();
    expect(await grantApprovalButton.isDisabled()).toBeTrue();
  }));

  it('shows disabled grant approval button if the current user is the requestor', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(newGrrUser({name: 'testuser'}));
    const {harness} = await createComponent(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
        requestor: 'testuser',
      }),
    );

    const grantApprovalButton = await harness.getGrantApprovalButton();
    expect(await grantApprovalButton.isDisabled()).toBeTrue();
  }));

  it('shows disabled grant approval button if the current user already approved', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(newGrrUser({name: 'approver'}));
    const {harness} = await createComponent(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
        approvers: ['approver'],
      }),
    );

    const grantApprovalButton = await harness.getGrantApprovalButton();
    expect(await grantApprovalButton.isDisabled()).toBeTrue();
  }));

  it('shows no warning chip if the approval time is less than default', fakeAsync(async () => {
    globalStoreMock.uiConfig = signal({
      defaultAccessDurationSeconds: 28 * 24 * 60 * 60, // 28 days in seconds
    });
    const {harness} = await createComponent(
      newClientApproval({
        expirationTime: new Date(
          // 28 days from now.
          Date.now() + 28 * 24 * 60 * 60 * 1000,
        ),
      }),
    );

    const approvalCard = await harness.approvalCard();
    expect(approvalCard).toBeDefined();
    expect(await approvalCard!.getText()).not.toContain(
      'longer than the default of 28 days. ',
    );
  }));

  it('shows warning chip if the approval time is longer than default', fakeAsync(async () => {
    globalStoreMock.uiConfig = signal({
      defaultAccessDurationSeconds: 30 * 24 * 60 * 60, // 30 days in seconds
    });
    const {harness} = await createComponent(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
        expirationTime: new Date(
          // 400 days from now.
          Date.now() + 400 * 24 * 60 * 60 * 1000,
        ),
      }),
    );

    const approvalCard = await harness.approvalCard();
    expect(approvalCard).toBeDefined();
    expect(await approvalCard!.getText()).toContain(
      'warning This duration is longer than the default of 30 days. ',
    );
  }));
});
