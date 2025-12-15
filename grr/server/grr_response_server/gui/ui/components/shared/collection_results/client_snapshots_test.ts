import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ClientSnapshot as ApiClientSnapshot,
  CloudInstanceInstanceType,
  NetworkAddressFamily,
} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {ClientSnapshots} from './client_snapshots';
import {ClientSnapshotsHarness} from './testing/client_snapshots_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(ClientSnapshots);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientSnapshotsHarness,
  );

  return {fixture, harness};
}

describe('Client Snapshots Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ClientSnapshots, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows a complete client snapshot', fakeAsync(async () => {
    const clientSnapshot: ApiClientSnapshot = {
      clientId: 'C.1234',
      filesystems: [
        {
          device: 'test-device',
          mountPoint: '/test-mount-point',
          type: 'test-type',
        },
      ],
      osRelease: 'test-os-release',
      osVersion: 'test-os-version',
      arch: 'test-arch',
      installTime: '1735693200000000', // 2025-01-01 01:00:00 UTC
      knowledgeBase: {
        fqdn: 'test-fqdn',
        os: 'test-os',
        osMajorVersion: 1111,
        osMinorVersion: 2222,
        users: [
          {
            username: 'test-username',
            homedir: '/test-homedir',
            uid: 1234,
            gid: 4321,
            shell: '/test-shell',
          },
        ],
      },
      grrConfiguration: [
        {
          key: 'test-key',
          value: 'test-value',
        },
      ],
      kernel: 'test-kernel',
      volumes: [
        {
          isMounted: true,
          name: 'test-name',
          devicePath: 'test-device-path',
          fileSystemType: 'test-file-system-type',
          totalAllocationUnits: '1',
          sectorsPerAllocationUnit: '2',
          bytesPerSector: '1024',
          actualAvailableAllocationUnits: '10',
          creationTime: '1735693200000000', // 2025-01-01 01:00:00 UTC
          serialNumber: 'test-serial-number',
        },
      ],
      interfaces: [
        {
          macAddress: 'qqusra6v',
          ifname: 'test-ifname',
          addresses: [
            {
              addressType: NetworkAddressFamily.INET,
              packedBytes: 'gAAAAQ==',
            },
            {
              addressType: NetworkAddressFamily.INET6,
              packedBytes: '8AAAAAAAAAAAAAAAAAAAAQ==',
            },
          ],
        },
      ],
      hardwareInfo: {
        serialNumber: 'test-serial-number',
        systemManufacturer: 'test-system-manufacturer',
        systemProductName: 'test-system-product-name',
        systemUuid: 'test-system-uuid',
        systemSkuNumber: 'test-system-sku-number',
        systemFamily: 'test-system-family',
        biosVendor: 'test-bios-vendor',
        biosVersion: 'test-bios-version',
        biosReleaseDate: 'test-release-date',
        biosRomSize: 'test-bios-rom-size',
        biosRevision: 'test-bios-revision',
        systemAssettag: 'test-system-assettag',
      },
      memorySize: '100',
      cloudInstance: {
        cloudType: CloudInstanceInstanceType.GOOGLE,
        google: {
          uniqueId: 'test-unique-id',
          zone: 'test-zone',
          projectId: 'test-project-id',
          instanceId: 'test-instance-id',
          hostname: 'test-hostname',
          machineType: 'test-machine-type',
        },
      },
      startupInfo: {
        clientInfo: {
          clientName: 'test-client-name',
          clientVersion: 999,
          revision: '888',
          buildTime: '2025-01-01T12:34:56.789Z',
          clientBinaryName: 'test-client-binary-name',
          clientDescription: 'test-client-description',
          labels: ['test-label'],
          timelineBtimeSupport: true,
          sandboxSupport: true,
        },
        bootTime: '1735693200000000', // 2025-01-01 01:00:00 UTC
        timestamp: '1735696800000000', // 2025-01-01 02:00:00 UTC
      },
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.CLIENT_SNAPSHOT,
        payload: clientSnapshot,
      }),
    ]);

    expect(await harness.clientSnapshots()).toHaveSize(1);
    const knowledgeBaseDetails = await harness.getKnowledgeBaseDetails(0);
    const knowledgeBaseTable = await knowledgeBaseDetails.table();
    expect(await knowledgeBaseTable.text()).toContain('test-os');
    expect(await knowledgeBaseTable.text()).toContain('1111');
    expect(await knowledgeBaseTable.text()).toContain('2222');
    expect(await knowledgeBaseTable.text()).toContain('test-fqdn');
    const osSectionText = await harness.getOperatingSystemTableText(0);
    expect(osSectionText).toContain('test-os-version');
    expect(osSectionText).toContain('test-os-release');
    expect(osSectionText).toContain('test-kernel');
    expect(osSectionText).toContain('2025-01-01 01:00:00 UTC');
    const usersDetails = await harness.getUsersDetails(0);
    const usersDetailsRows = await usersDetails.getRowTexts();
    expect(usersDetailsRows[0]).toContain('test-username');
    expect(usersDetailsRows[1]).toContain('/test-homedir');
    expect(usersDetailsRows[2]).toContain('1234');
    expect(usersDetailsRows[3]).toContain('4321');
    expect(usersDetailsRows[4]).toContain('/test-shell');
    const cloudInstanceDetails = await harness.getCloudInstanceDetails(0);
    const cloudInstanceTable = await cloudInstanceDetails.table();
    expect(await cloudInstanceTable.text()).toContain('GOOGLE');
    expect(await cloudInstanceTable.text()).toContain('test-unique-id');
    expect(await cloudInstanceTable.text()).toContain('test-zone');
    expect(await cloudInstanceTable.text()).toContain('test-project-id');
    expect(await cloudInstanceTable.text()).toContain('test-instance-id');
    expect(await cloudInstanceTable.text()).toContain('test-hostname');
    expect(await cloudInstanceTable.text()).toContain('test-machine-type');
    const startupInfoDetails = await harness.getStartupInfoDetails(0);
    const startupInfoTable = await startupInfoDetails.table();
    expect(await startupInfoTable.text()).toContain('Boot Time');
    expect(await startupInfoTable.text()).toContain('2025-01-01 01:00:00 UTC');
    expect(await startupInfoTable.text()).toContain('Client Name');
    expect(await startupInfoTable.text()).toContain('test-client-name');
    expect(await startupInfoTable.text()).toContain('Client Version');
    expect(await startupInfoTable.text()).toContain('999');
    expect(await startupInfoTable.text()).toContain('Build Time');
    expect(await startupInfoTable.text()).toContain('2025-01-01 12:34:56 UTC');
    expect(await startupInfoTable.text()).toContain('Binary Name');
    expect(await startupInfoTable.text()).toContain('test-client-binary-name');
    expect(await startupInfoTable.text()).toContain('Description');
    expect(await startupInfoTable.text()).toContain('test-client-description');
    expect(await startupInfoTable.text()).toContain('Capabilities');
    expect(await startupInfoTable.text()).toContain(
      'check Sandboxing supported',
    );
    expect(await startupInfoTable.text()).toContain(
      'check Btime field in Timeline flow supported',
    );
    const hardwareTableText = await harness.getHardwareTableText(0);
    expect(hardwareTableText).toContain('CPU Architecture');
    expect(hardwareTableText).toContain('test-arch');
    expect(hardwareTableText).toContain('Memory Size');
    expect(hardwareTableText).toContain('100');
    const hardwareInfoDetails = await harness.getHardwareInfoDetails(0);
    const hardwareInfoTable = await hardwareInfoDetails.table();
    expect(await hardwareInfoTable.text()).toContain('Manufacturer');
    expect(await hardwareInfoTable.text()).toContain(
      'test-system-manufacturer',
    );
    expect(await hardwareInfoTable.text()).toContain('Family');
    expect(await hardwareInfoTable.text()).toContain('test-system-family');
    expect(await hardwareInfoTable.text()).toContain('Product Name');
    expect(await hardwareInfoTable.text()).toContain(
      'test-system-product-name',
    );
    expect(await hardwareInfoTable.text()).toContain('Serial Number');
    expect(await hardwareInfoTable.text()).toContain('test-serial-number');
    expect(await hardwareInfoTable.text()).toContain('UUID');
    expect(await hardwareInfoTable.text()).toContain('test-system-uuid');
    expect(await hardwareInfoTable.text()).toContain('SKU Number');
    expect(await hardwareInfoTable.text()).toContain('test-system-sku-number');
    expect(await hardwareInfoTable.text()).toContain('Asset Tag');
    expect(await hardwareInfoTable.text()).toContain('test-system-assettag');
    expect(await hardwareInfoTable.text()).toContain('BIOS Vendor');
    expect(await hardwareInfoTable.text()).toContain('test-bios-vendor');
    expect(await hardwareInfoTable.text()).toContain('BIOS Version');
    expect(await hardwareInfoTable.text()).toContain('test-bios-version');
    expect(await hardwareInfoTable.text()).toContain('BIOS Release Date');
    expect(await hardwareInfoTable.text()).toContain('test-release-date');
    expect(await hardwareInfoTable.text()).toContain('BIOS ROM Size');
    expect(await hardwareInfoTable.text()).toContain('test-bios-rom-size');
    expect(await hardwareInfoTable.text()).toContain('BIOS Revision');
    expect(await hardwareInfoTable.text()).toContain('test-bios-revision');
    const volumeDetails = await harness.getVolumesDetails(0);
    const volumeDetailsRows = await volumeDetails.getRowTexts();
    expect(volumeDetailsRows[0]).toContain('test-name');
    expect(volumeDetailsRows[1]).toContain('test-device-path');
    expect(volumeDetailsRows[2]).toContain('test-file-system-type');
    expect(volumeDetailsRows[3]).toContain('2.00 KiB');
    expect(volumeDetailsRows[4]).toContain('20.00 KiB');
    expect(volumeDetailsRows[5]).toContain('1.00 KiB');
    expect(volumeDetailsRows[6]).toContain('2025-01-01 01:00:00 UTC');
    const networkInterfacesDetails =
      await harness.getNetworkInterfacesDetails(0);
    const networkInterfacesDetailsRows =
      await networkInterfacesDetails.getRowTexts();
    expect(networkInterfacesDetailsRows[0]).toContain('test-ifname');
    expect(networkInterfacesDetailsRows[1]).toContain('AA:AB:AC:AD:AE:AF');
    expect(networkInterfacesDetailsRows[2]).toContain('128.0.0.1');
    expect(networkInterfacesDetailsRows[2]).toContain(
      'F000:0000:0000:0000:0000:0000:0000:0001',
    );
  }));

  it('shows several client snapshots', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.CLIENT_SNAPSHOT,
        payload: {
          clientId: 'C.1234',
        },
      }),
      newFlowResult({
        payloadType: PayloadType.CLIENT_SNAPSHOT,
        payload: {
          clientId: 'C.1234',
        },
      }),
    ]);

    expect(await harness.clientSnapshots()).toHaveSize(2);
  }));

  it('shows client id for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payload: {
          clientId: 'C.1234',
        },
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(1);
    expect(await clientIds[0].text()).toContain('Client ID: C.1234');
  }));

  it('does not show client id for flow results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        clientId: 'C.1234',
        payload: {
          clientId: 'C.1234',
        },
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(0);
  }));
});
