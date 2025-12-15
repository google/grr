import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {
  newClientApproval,
  newHuntApproval,
} from '../../../lib/models/model_test_util';
import {Approval} from '../../../lib/models/user';
import {initTestEnvironment} from '../../../testing';
import {PendingApproval} from './pending_approval';
import {PendingApprovalHarness} from './testing/pending_approval_harness';

initTestEnvironment();

async function createComponent(approval: Approval) {
  const fixture = TestBed.createComponent(PendingApproval);
  fixture.componentRef.setInput('approval', approval);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    PendingApprovalHarness,
  );

  return {fixture, harness};
}

describe('Pending Approval Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [PendingApproval, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent(newClientApproval());

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows requested approvers', async () => {
    const {harness} = await createComponent(
      newClientApproval({
        requestedApprovers: ['approver1', 'approver2'],
      }),
    );

    const requestedApprovers = await harness.requestedApprovers();

    expect(requestedApprovers).toHaveSize(2);
    expect(await requestedApprovers[0].getUsername()).toBe('approver1');
    expect(await requestedApprovers[1].getUsername()).toBe('approver2');
  });

  it('shows reason', async () => {
    const {harness} = await createComponent(
      newClientApproval({
        reason: 'Banana!!!',
      }),
    );

    expect(await harness.getReasonText()).toBe('Banana!!!');
  });

  it('shows Client approval URL', async () => {
    const {harness} = await createComponent(
      newClientApproval({
        clientId: 'C.1234',
        requestor: 'requestor',
        approvalId: '1234',
      }),
    );

    expect(
      await harness.showsCopyButtonWithApprovalUrl(
        /.*\/clients\/C.1234\/approvals\/1234\/users\/requestor/,
      ),
    ).toBeTrue();
  });

  it('shows Fleet Collection approval URL', async () => {
    const {harness} = await createComponent(
      newHuntApproval({
        huntId: 'H.1234',
        requestor: 'requestor',
        approvalId: '1234',
      }),
    );
    expect(
      await harness.showsCopyButtonWithApprovalUrl(
        /.*\/fleet-collections\/H.1234\/approvals\/1234\/users\/requestor/,
      ),
    ).toBeTrue();
  });
});
