import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {CloudInstanceInstanceType} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {newClientSnapshot} from '../../../lib/models/model_test_util';
import {ClientStore} from '../../../store/client_store';
import {
  ClientStoreMock,
  newClientStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {ClientHistoryEntry} from './client_history_entry';
import {ClientHistoryEntryHarness} from './testing/client_history_entry_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientHistoryEntry);

  fixture.detectChanges();
  const loader = TestbedHarnessEnvironment.loader(fixture);
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientHistoryEntryHarness,
  );

  return {fixture, harness, loader};
}

describe('Client History Entry Component', () => {
  let clientStoreMock: ClientStoreMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();

    TestBed.configureTestingModule({
      imports: [
        ClientHistoryEntry,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('shows complete `Snapshot` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        sourceFlowId: '9876',
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    expect(await harness.hasSnapshotSection()).toBeTrue();
    const snapshontSectionText = await harness.getSnapshotSectionText();

    expect(snapshontSectionText).toContain('Client');
    expect(snapshontSectionText).toContain('C.1234');

    expect(snapshontSectionText).toContain('Source Flow');
    expect(snapshontSectionText).toContain('9876');

    expect(snapshontSectionText).toContain('Collected at');
    expect(snapshontSectionText).toContain('2024-01-01 00:00:00 UTC');
  }));

  it('skips missing fields in `Snapshot` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        // No source flow ID.
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const snapshontSectionText = await harness.getSnapshotSectionText();
    expect(snapshontSectionText).toContain('Client');
    expect(snapshontSectionText).toContain('C.1234');

    expect(snapshontSectionText).not.toContain('Source Flow');

    expect(snapshontSectionText).toContain('Collected at');
    expect(snapshontSectionText).toContain('2024-01-01 00:00:00 UTC');
  }));

  it('shows complete `Operating System` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00.000Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        osRelease: 'Bar',
        osVersion: 'Baz',
        kernel: 'Nut',
        installTime: new Date('2024-01-01T00:00:00.000Z'),
        knowledgeBase: {},
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    expect(await harness.hasOsSection()).toBeTrue();
    const osSectionText = await harness.getOsSectionText();

    expect(osSectionText).toContain('Release');
    expect(osSectionText).toContain('Bar');

    expect(osSectionText).toContain('Version');
    expect(osSectionText).toContain('Baz');

    expect(osSectionText).toContain('Kernel');
    expect(osSectionText).toContain('Nut');
    expect(osSectionText).toContain('Install Date');
    expect(osSectionText).toContain('2024-01-01 00:00:00 UTC');

    expect(await harness.knowledgeBaseDetailsHarness()).toBeDefined();
  }));

  it('skips missing fields in `Operating System` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        // No OS info.
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const osSectionText = await harness.getOsSectionText();
    // Operating System section is always shown, but it might be empty.
    expect(osSectionText).toContain('Operating System');

    expect(osSectionText).not.toContain('Release');
    expect(osSectionText).not.toContain('Version');
    expect(osSectionText).not.toContain('Kernel');
    expect(osSectionText).not.toContain('Install Date');
    expect(osSectionText).toContain('Knowledge Base');
    const knowledgeBaseHarness = await harness.knowledgeBaseDetailsHarness();
    const knowledgebaseTable = await knowledgeBaseHarness?.table();
    expect(knowledgebaseTable).toBeDefined();
    expect(await knowledgebaseTable?.text()).toBe('');
  }));

  it('shows complete `Users` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        users: [
          {
            username: 'testuser',
            fullName: 'Test User',
            lastLogon: new Date('2020-07-01T13:00:00.000Z'),
            homedir: '/home/testuser',
            uid: 54321,
            gid: 12345,
            shell: '/bin/bash',
          },
          {
            username: 'testuser2',
            fullName: 'Test User 2',
            lastLogon: new Date('2020-07-01T13:00:00.000Z'),
            homedir: '/home/testuser2',
            uid: 654321,
            gid: 23456,
            shell: '/bin/bash2',
          },
          {
            username: 'testuser3',
            fullName: 'Test User 3',
            lastLogon: new Date('2020-07-01T13:00:00.000Z'),
            homedir: '/home/testuser3',
            uid: 7654321,
            gid: 34567,
            shell: '/bin/bash3',
          },
        ],
      }),
    ]);
    const {harness, fixture, loader} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const usersHarness = await harness.getUserDetailsHarness();
    expect(await usersHarness?.numTables()).toBe(1);
    const showMoreUsersButton = await (
      await loader.getChildLoader('[name="users-section"]')
    ).getHarness(MatButtonHarness.with({text: /more/}));
    await showMoreUsersButton.click();
    expect(await usersHarness?.numTables()).toBe(3);
    const showLessUsersButton = await (
      await loader.getChildLoader('[name="users-section"]')
    ).getHarness(MatButtonHarness.with({text: /less/}));
    await showLessUsersButton.click();
    expect(await usersHarness?.numTables()).toBe(1);
  }));

  it('shows empty `Users` section if there are no users', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        // No users.
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const usersHarness = await harness.getUserDetailsHarness();
    expect(await usersHarness?.hasNoneText()).toBeTrue();
  }));

  it('shows `Cloud` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        cloudInstance: {
          cloudType: CloudInstanceInstanceType.GOOGLE,
          google: {},
        },
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    expect(await harness.hasCloudSection()).toBeTrue();
    expect(await harness.cloudInstanceDetailsHarness()).toBeDefined();
  }));

  it('skips `Cloud` section if no cloud instance', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        // No cloud instance.
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    expect(await harness.hasCloudSection()).toBeFalse();
  }));

  it('shows complete `Agents` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00.000Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        startupInfo: {
          clientInfo: {
            clientName: 'test-client',
            clientVersion: 9876,
            buildTime: new Date('2024-01-01T00:00:00.000Z'),
            clientBinaryName: 'test-client-binary',
            clientDescription: 'test-client-description',
            sandboxSupport: true,
            timelineBtimeSupport: true,
          },
        },
      }),
    ]);

    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    expect(await harness.hasAgentSection()).toBeTrue();
    const agentsSectionText = await harness.getAgentSectionText();

    expect(agentsSectionText).toContain('Client Name');
    expect(agentsSectionText).toContain('test-client');

    expect(agentsSectionText).toContain('Version');
    expect(agentsSectionText).toContain('9876');

    expect(agentsSectionText).toContain('Build Time');
    expect(agentsSectionText).toContain('2024-01-01 00:00:00 UTC');

    expect(agentsSectionText).toContain('Binary Name');
    expect(agentsSectionText).toContain('test-client-binary');

    expect(agentsSectionText).toContain('Description');
    expect(agentsSectionText).toContain('test-client-description');

    expect(agentsSectionText).toContain('Capabilities');
    expect(agentsSectionText).toContain('Sandboxing supported');
    expect(agentsSectionText).toContain(
      'Btime field in Timeline flow supported',
    );
  }));

  it('skips missing fields in `Agents` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        // No agent info.
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);
    tick();

    const agentsSectionText = await harness.getAgentSectionText();
    expect(agentsSectionText).not.toContain('Client Name');
    expect(agentsSectionText).not.toContain('Version');
    expect(agentsSectionText).not.toContain('Build Time');
    expect(agentsSectionText).not.toContain('Binary Name');
    expect(agentsSectionText).not.toContain('Description');
    expect(agentsSectionText).not.toContain('Capabilities');
    expect(agentsSectionText).not.toContain('Sandboxing');
    expect(agentsSectionText).not.toContain('Btime field in Timeline flow');
  }));

  it('shows complete `Hardware` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        memorySize: BigInt(1 * 1024 * 1024),
        arch: 'test-machine',
        hardwareInfo: {},
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    expect(await harness.hasHardwareSection()).toBeTrue();
    const hardwareSectionText = await harness.getHardwareSectionText();

    expect(hardwareSectionText).toContain('CPU Architecture');
    expect(hardwareSectionText).toContain('test-machine');

    expect(hardwareSectionText).toContain('Memory Size');
    expect(hardwareSectionText).toContain('1.00 MiB');

    const hardwareInfoHarness = await harness.hardwareInfoDetailsHarness();
    expect(hardwareInfoHarness).toBeDefined();
  }));

  it('skips missing fields in `Hardware` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const hardwareSectionText = await harness.getHardwareSectionText();
    // Hardware section is always shown but empty fields are skipped.
    expect(hardwareSectionText).toContain('Hardware');

    expect(hardwareSectionText).not.toContain('CPU Architecture');
    expect(hardwareSectionText).not.toContain('Memory Size');
    expect(hardwareSectionText).toContain('Hardware Info');

    // Hardware info is shown but will be empty.
    const hardwareInfoHarness = await harness.hardwareInfoDetailsHarness();
    const hardwareInfoTable = await hardwareInfoHarness?.table();
    expect(hardwareInfoTable).toBeDefined();
    expect(await hardwareInfoTable?.text()).toBe('');
  }));

  it('shows complete `Volumes` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        volumes: [
          {
            devicePath: '/dev/sda1',
          },
          {
            devicePath: '/dev/sda2',
          },
          {
            devicePath: '/dev/sda3',
          },
        ],
      }),
    ]);
    const {harness, fixture, loader} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const volumesHarness = await harness.getVolumesHarness();
    expect(await volumesHarness?.numTables()).toBe(2);

    const showMoreVolumesButton = await (
      await loader.getChildLoader('[name="volumes-section"]')
    ).getHarness(MatButtonHarness.with({text: /more/}));
    await showMoreVolumesButton.click();
    expect(await volumesHarness?.numTables()).toBe(3);

    const showLessVolumesButton = await (
      await loader.getChildLoader('[name="volumes-section"]')
    ).getHarness(MatButtonHarness.with({text: /less/}));
    await showLessVolumesButton.click();
    expect(await volumesHarness?.numTables()).toBe(2);
  }));

  it('shows empty `Volumes` section if no volumes', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        // No volumes.
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const volumesHarness = await harness.getVolumesHarness();
    expect(await volumesHarness?.hasNoneText()).toBeTrue();
  }));

  it('shows complete `Network Interfaces` section', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        networkInterfaces: [
          {macAddress: 'my:mac:address', addresses: []},
          {macAddress: 'another:mac:address', addresses: []},
          {macAddress: 'yet:another:mac:address', addresses: []},
          {macAddress: 'yet:yet:another:mac:address', addresses: []},
        ],
      }),
    ]);
    const {harness, fixture, loader} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const networkInterfacesHarness =
      await harness.getNetworkInterfacesHarness();
    expect(await networkInterfacesHarness?.numTables()).toBe(3);

    const showMoreNetworkInterfacesButton = await (
      await loader.getChildLoader('[name="network-section"]')
    ).getHarness(MatButtonHarness.with({text: /more/}));
    await showMoreNetworkInterfacesButton.click();

    expect(await networkInterfacesHarness?.numTables()).toBe(4);

    const showLessNetworkInterfacesButton = await (
      await loader.getChildLoader('[name="network-section"]')
    ).getHarness(MatButtonHarness.with({text: /less/}));
    await showLessNetworkInterfacesButton.click();

    expect(await networkInterfacesHarness?.numTables()).toBe(3);
  }));

  it('shows empty `Network Interfaces` section if no network interfaces', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientSnapshots = signal([
      newClientSnapshot({
        clientId: 'C.1234',
        timestamp: snapshotDate,
        // No network interfaces.
      }),
    ]);
    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    const networkInterfacesHarness =
      await harness.getNetworkInterfacesHarness();
    expect(await networkInterfacesHarness?.hasNoneText()).toBeTrue();
  }));

  it('shows complete `Startup Info` section for startup info', fakeAsync(async () => {
    const snapshotDate = new Date('2024-01-01T00:00:00.000Z');
    clientStoreMock.clientId = signal('C.1234');
    clientStoreMock.clientStartupInfos = signal([
      {
        timestamp: snapshotDate,
        clientInfo: {
          clientName: 'test-client',
          clientVersion: 9876,
          buildTime: new Date('2024-01-01T00:00:00.000Z'),
          clientBinaryName: 'test-client-binary',
          clientDescription: 'test-client-description',
          sandboxSupport: true,
          timelineBtimeSupport: true,
        },
      },
    ]);

    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('historyTimestamp', snapshotDate);

    expect(await harness.hasStartupInfoSection()).toBeTrue();
    const startupInfoSectionText = await harness.getStartupInfoSectionText();

    expect(startupInfoSectionText).toContain('Client Name');
    expect(startupInfoSectionText).toContain('test-client');

    expect(startupInfoSectionText).toContain('Version');
    expect(startupInfoSectionText).toContain('9876');

    expect(startupInfoSectionText).toContain('Build Time');
    expect(startupInfoSectionText).toContain('2024-01-01 00:00:00 UTC');

    expect(startupInfoSectionText).toContain('Binary Name');
    expect(startupInfoSectionText).toContain('test-client-binary');

    expect(startupInfoSectionText).toContain('Description');
    expect(startupInfoSectionText).toContain('test-client-description');

    expect(startupInfoSectionText).toContain('Capabilities');
    expect(startupInfoSectionText).toContain('Sandboxing supported');
    expect(startupInfoSectionText).toContain(
      'Btime field in Timeline flow supported',
    );
  }));
});
