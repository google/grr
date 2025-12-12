import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';

import {newApproval} from '../../lib/models/model_test_util';
import {initTestEnvironment} from '../../testing';
import {ApprovalChip} from './approval_chip';
import {ApprovalChipHarness} from './testing/approval_chip_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ApprovalChip);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ApprovalChipHarness,
  );
  return {fixture, harness};
}

describe('Approval Chip Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ApprovalChip],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('shows "No access" for missing approval', async () => {
    const {fixture, harness} = await createComponent();

    fixture.componentRef.setInput('approval', undefined);
    expect(await harness.isAccessDeniedChipVisible()).toBeTrue();
  });

  it('shows "No access" for expired approval', async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput(
      'approval',
      newApproval({
        status: {type: 'expired', reason: ''},
      }),
    );
    expect(await harness.isAccessDeniedChipVisible()).toBeTrue();
  });

  it('shows "No access" for invalid approval', async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput(
      'approval',
      newApproval({
        status: {type: 'invalid', reason: ''},
      }),
    );
    expect(await harness.isAccessDeniedChipVisible()).toBeTrue();
  });

  it('shows "Access granted" for valid approval', async () => {
    const {fixture, harness} = await createComponent();

    fixture.componentRef.setInput(
      'approval',
      newApproval({status: {type: 'valid'}}),
    );
    expect(await harness.isAccessGrantedChipVisible()).toBeTrue();
  });

  it('shows "Access pending" for pending approval', async () => {
    const {fixture, harness} = await createComponent();

    fixture.componentRef.setInput(
      'approval',
      newApproval({status: {type: 'pending', reason: 'Need 1 more approver'}}),
    );
    expect(await harness.isAccessPendingChipVisible()).toBeTrue();
  });

  it('shows time left for valid approval', async () => {
    const mockNow = new Date('2020-07-01T13:00:00.000');
    jasmine.clock().mockDate(mockNow);

    const threeDaysMs = 1000 * 60 * 60 * 24 * 3;
    const oneHourMs = 1000 * 60 * 60;
    const mockExpirationTimeMs = mockNow.getTime() + threeDaysMs + oneHourMs;

    const {fixture, harness} = await createComponent();

    fixture.componentRef.setInput(
      'approval',
      newApproval({
        status: {type: 'valid'},
        expirationTime: new Date(mockExpirationTimeMs),
      }),
    );
    expect(await harness.isAccessGrantedChipVisible()).toBeTrue();
    expect(await harness.getAccessGrantedChipText()).toContain('3 days left');
  });

  it('shows 61 minutes left as "1 hour left"', async () => {
    const mockNow = new Date('2020-07-01T13:00:00.000');
    jasmine.clock().mockDate(mockNow);
    const sixtyOneMinutesMs = 1000 * 60 * 61;
    const mockExpirationTimeMs = mockNow.getTime() + sixtyOneMinutesMs;

    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput(
      'approval',
      newApproval({
        status: {type: 'valid'},
        expirationTime: new Date(mockExpirationTimeMs),
      }),
    );
    expect(await harness.isAccessGrantedChipVisible()).toBeTrue();
    expect(await harness.getAccessGrantedChipText()).toContain('1 hour left');
  });
});
