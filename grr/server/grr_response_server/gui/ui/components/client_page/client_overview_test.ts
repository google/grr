import {TestElement} from '@angular/cdk/testing';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {newClient, newClientApproval} from '../../lib/models/model_test_util';
import {ClientStore} from '../../store/client_store';
import {GlobalStore} from '../../store/global_store';
import {
  ClientStoreMock,
  GlobalStoreMock,
  newClientStoreMock,
  newGlobalStoreMock,
} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {ClientOverview} from './client_overview';
import {ClientOverviewHarness} from './testing/client_overview_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientOverview);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientOverviewHarness,
  );

  return {fixture, harness};
}

describe('Client Overview', () => {
  let globalStoreMock: GlobalStoreMock;
  let clientStoreMock: ClientStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();
    clientStoreMock = newClientStoreMock();

    TestBed.configureTestingModule({
      imports: [
        ClientOverview,
        NoopAnimationsModule,
        RouterModule.forRoot([], {bindToComponentInputs: true}),
      ],
      providers: [
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('displays empty client details if client is not set', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(null);
    tick();

    const {harness} = await createComponent();

    expect(await harness.getClientNameText()).toBe('C.1234');

    expect(await harness.getIdText()).toContain('C.1234');

    expect(await harness.getFqdnText()).toContain('FQDN:');
    expect(await harness.getOsText()).toContain('OS:');
    expect(await harness.getUsersText()).toBe('Users:');
    expect(await harness.getGRRAgentText()).toContain('GRR agent:');
    expect(await harness.getGRRAgentBuildText()).toBe('GRR agent built time:');
    expect(await harness.getRRGAgentText()).toContain('RRG agent:');
    expect(await harness.getFirstSeenText()).toBe('First seen:');
    expect(await harness.getLastSeenText()).toBe('Last seen:');
    expect(await harness.getLastBootedAtText()).toBe('Last booted at:');
  }));

  it('displays client details', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({
        clientId: 'C.1234',
        knowledgeBase: {
          fqdn: 'foo.bar',
        },
        osInfo: {
          system: 'any system',
          version: 'any os version',
          kernel: 'any kernel',
        },
        users: [
          {
            username: 'ba',
            uid: 1111,
          },
          {
            username: 'nana',
            uid: 2222,
          },
        ],
        agentInfo: {
          clientVersion: 1234,
          clientDescription: 'foo description',
          buildTime: new Date(1743085000000),
        },
        rrgVersion: '1.2.3',
        firstSeenAt: new Date(1743086000000),
        lastSeenAt: new Date(1743087000000),
        lastBootedAt: new Date(1743088000000),
      }),
    );
    tick();

    const {harness} = await createComponent();

    expect(await harness.getClientNameText()).toBe('foo.bar');

    expect(await harness.getIdText()).toContain('C.1234');

    expect(await harness.getFqdnText()).toContain('FQDN:');
    expect(await harness.getFqdnText()).toContain('foo.bar');

    expect(await harness.getOsText()).toContain('OS:');
    expect(await harness.getOsText()).toContain(
      'any system any os version any kernel',
    );

    expect(await harness.getUsersText()).toContain('Users:');
    expect(await harness.getUsersText()).toContain('ba, nana');

    expect(await harness.getGRRAgentText()).toContain('GRR agent:');
    expect(await harness.getGRRAgentText()).toContain('foo description 1234');

    expect(await harness.getGRRAgentBuildText()).toContain(
      'GRR agent built time:',
    );
    expect(await harness.getGRRAgentBuildText()).toContain(
      '2025-03-27 14:16:40 UTC',
    );

    expect(await harness.getRRGAgentText()).toContain('RRG agent:');
    expect(await harness.getRRGAgentText()).toContain('1.2.3');

    expect(await harness.getFirstSeenText()).toContain('First seen:');
    expect(await harness.getFirstSeenText()).toContain(
      '2025-03-27 14:33:20 UTC',
    );

    expect(await harness.getLastSeenText()).toContain('Last seen:');
    expect(await harness.getLastSeenText()).toContain(
      '2025-03-27 14:50:00 UTC',
    );

    expect(await harness.getLastBootedAtText()).toContain('Last booted at:');
    expect(await harness.getLastBootedAtText()).toContain(
      '2025-03-27 15:06:40 UTC',
    );
  }));

  it('shows all client labels', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({
        clientId: 'C.1234',
        labels: [
          {name: 'label1', owner: 'owner1'},
          {name: 'label2', owner: 'owner2'},
        ],
      }),
    );
    tick();

    const {harness} = await createComponent();

    const labels = await harness.getAllLabelChipTexts();
    expect(labels).toEqual(['label1', 'label2']);
  }));

  it('shows add label button if the client is set', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(newClient({clientId: 'C.1234'}));
    tick();

    const {harness} = await createComponent();
    expect(await harness.isAddLabelButtonVisible()).toBeTrue();
  }));

  it('shows online chip if the client last_seen is recent', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({clientId: 'C.1234', lastSeenAt: new Date(Date.now())}),
    );
    tick();

    const {harness} = await createComponent();
    const onlineChipHarness = await harness.getOnlineChipHarness();

    expect(await onlineChipHarness.hasOnlineChip()).toBeTrue();
  }));

  it('shows offline chip if the client last_seen is not recent', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({
        clientId: 'C.1234',
        lastSeenAt: new Date(Date.now() - 1000 * 60 * 16),
      }),
    );
    tick();

    const {harness} = await createComponent();
    const onlineChipHarness = await harness.getOnlineChipHarness();
    expect(await onlineChipHarness.hasOfflineChip()).toBeTrue();
  }));

  it('shows approval chip if the user access is not set and no approval', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(null);
    clientStoreMock.latestApproval = signal(null);
    tick();

    const {harness} = await createComponent();
    expect(await harness.isApprovalChipVisible()).toBeTrue();
    const approvalChipHarness = await harness.getApprovalChipHarness();
    expect(await approvalChipHarness.isAccessDeniedChipVisible()).toBeTrue();
  }));

  it('shows approval chip if the user has no client access and no approval', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(false);
    clientStoreMock.latestApproval = signal(null);
    tick();

    const {harness} = await createComponent();
    expect(await harness.isApprovalChipVisible()).toBeTrue();
    const approvalChipHarness = await harness.getApprovalChipHarness();
    expect(await approvalChipHarness.isAccessDeniedChipVisible()).toBeTrue();
  }));

  it('shows approval chip if the user has no access and pending approval', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(false);
    clientStoreMock.latestApproval = signal(
      newClientApproval({
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    );
    tick();

    const {harness} = await createComponent();
    expect(await harness.isApprovalChipVisible()).toBeTrue();
    const approvalChipHarness = await harness.getApprovalChipHarness();
    expect(await approvalChipHarness.isAccessPendingChipVisible()).toBeTrue();
  }));

  it('shows no approval chip if the user has client access but no approval', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(true);
    clientStoreMock.latestApproval = signal(null);
    tick();

    const {harness} = await createComponent();
    expect(await harness.isApprovalChipVisible()).toBeFalse();
  }));

  it('sets the label chip href to the client search with label query', fakeAsync(async () => {
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({
        clientId: 'C.1234',
        labels: [{name: 'foo', owner: 'owner'}],
      }),
    );
    tick();

    const {harness} = await createComponent();
    const labelChip = await harness.getLabelChip('foo');
    // Get the parent <a> element of the label chip.
    const parentAnchor = await (
      await labelChip.host()
    ).getProperty<TestElement | null>('parentElement');
    if (!parentAnchor) {
      throw new Error('Label chip parent element not found');
    }

    const labelChiphref = await parentAnchor.getAttribute('href');
    expect(labelChiphref).toBe('/clients?q=label:foo');
  }));

  it('shows client warning for matching label', fakeAsync(async () => {
    globalStoreMock.uiConfig = signal({
      clientWarnings: {
        rules: [
          {
            message: 'foo warning',
            withLabels: ['foo'],
          },
        ],
      },
    });
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({
        clientId: 'C.1234',
        labels: [{name: 'foo', owner: 'owner'}],
      }),
    );

    const {harness} = await createComponent();
    const errorMessages = await harness.errorMessages();
    expect(errorMessages.length).toBe(1);
    expect(await errorMessages[0].getMessage()).toBe('foo warning');
  }));

  it('does not show client warning for non-matching label', fakeAsync(async () => {
    globalStoreMock.uiConfig = signal({
      clientWarnings: {
        rules: [
          {
            message: 'foo warning',
            withLabels: ['foo'],
          },
        ],
      },
    });
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({
        clientId: 'C.1234',
        labels: [{name: 'bar', owner: 'owner'}],
      }),
    );

    const {harness} = await createComponent();
    const errorMessages = await harness.errorMessages();
    expect(errorMessages.length).toBe(0);
  }));

  it('shows multiple client warnings for matching labels', fakeAsync(async () => {
    globalStoreMock.uiConfig = signal({
      clientWarnings: {
        rules: [
          {
            message: 'foo warning',
            withLabels: ['foo'],
          },
          {
            message: 'bar warning',
            withLabels: ['bar'],
          },
        ],
      },
    });
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.client = signal(
      newClient({
        clientId: 'C.1234',
        labels: [
          {name: 'foo', owner: 'owner'},
          {name: 'bar', owner: 'owner'},
        ],
      }),
    );

    const {harness} = await createComponent();
    const errorMessages = await harness.errorMessages();
    expect(errorMessages.length).toBe(2);
    expect(await errorMessages[0].getMessage()).toBe('foo warning');
    expect(await errorMessages[1].getMessage()).toBe('bar warning');
  }));
});
