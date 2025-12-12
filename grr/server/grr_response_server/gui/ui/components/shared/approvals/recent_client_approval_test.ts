import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {ClientApproval} from '../../../lib/models/client';
import {
  newClient,
  newClientApproval,
} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {RecentClientApproval} from './recent_client_approval';
import {RecentClientApprovalHarness} from './testing/recent_client_approval_harness';

initTestEnvironment();

async function createComponent(approval: ClientApproval) {
  const fixture = TestBed.createComponent(RecentClientApproval);
  fixture.componentRef.setInput('approval', approval);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    RecentClientApprovalHarness,
  );

  return {fixture, harness};
}

describe('Recent Client Approval Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [
        RecentClientApproval,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES),
      ],
    }).compileComponents();
  }));

  it('is created', fakeAsync(async () => {
    const {fixture} = await createComponent(
      newClientApproval({
        clientId: 'C.1111',
        status: {type: 'valid'},
      }),
    );

    expect(fixture.componentInstance).toBeTruthy();
  }));

  it('displays client information when loaded', fakeAsync(async () => {
    const {harness} = await createComponent(
      newClientApproval({
        clientId: 'C.1111',
        subject: newClient({
          clientId: 'C.1111',
          knowledgeBase: {
            os: 'Linux',
            fqdn: 'test.com',
          },
          lastSeenAt: new Date(2020, 1, 1),
        }),
        reason: 'test reason',
        status: {type: 'invalid', reason: 'test reason'},
      }),
    );

    const clientLink = await harness.clientLink();
    expect(await clientLink.text()).toContain('test.com C.1111');
    const approvalChip = await harness.approvalChip();
    expect(await approvalChip.isAccessDeniedChipVisible()).toBeTrue();
    const onlineChip = await harness.onlineChip();
    expect(await onlineChip.hasOfflineChip()).toBeTrue();
    const approvalReason = await harness.approvalReason();
    expect(await approvalReason.text()).toContain('test reason');
  }));

  it('links to the client page', fakeAsync(async () => {
    const {harness} = await createComponent(
      newClientApproval({
        clientId: 'C.1111',
      }),
    );

    const clientLink = await harness.clientLink();
    await clientLink.click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual('/clients/C.1111/flows');
  }));
});
