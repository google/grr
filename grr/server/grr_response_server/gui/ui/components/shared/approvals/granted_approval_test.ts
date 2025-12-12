import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {newClientApproval} from '../../../lib/models/model_test_util';
import {Approval} from '../../../lib/models/user';
import {initTestEnvironment} from '../../../testing';
import {GrantedApproval} from './granted_approval';
import {GrantedApprovalHarness} from './testing/granted_approval_harness';

initTestEnvironment();

async function createComponent(approval: Approval) {
  const fixture = TestBed.createComponent(GrantedApproval);
  fixture.componentRef.setInput('approval', approval);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    GrantedApprovalHarness,
  );

  return {fixture, harness};
}

describe('Granted Approval Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [GrantedApproval, NoopAnimationsModule],
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

  it('shows approvers', async () => {
    const {harness} = await createComponent(
      newClientApproval({
        approvers: ['approver1', 'approver2'],
      }),
    );

    const approvers = await harness.approvers();

    expect(approvers).toHaveSize(2);
    expect(await approvers[0].getUsername()).toBe('approver1');
    expect(await approvers[1].getUsername()).toBe('approver2');
  });

  it('shows reason', async () => {
    const {harness} = await createComponent(
      newClientApproval({
        reason: 'Banana!!!',
      }),
    );

    expect(await harness.getReasonText()).toBe('Banana!!!');
  });
});
