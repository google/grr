import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HardwareInfo as ApiHardwareInfo} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {HardwareInfos} from './hardware_infos';
import {HardwareInfosHarness} from './testing/hardware_infos_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(HardwareInfos);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    HardwareInfosHarness,
  );

  return {fixture, harness};
}

describe('Hardware Infos Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HardwareInfos, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows complete hardware info result', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.HARDWARE_INFO,
        payload: {
          systemManufacturer: 'test-system-manufacturer',
          systemFamily: 'test-system-family',
          systemProductName: 'test-system-product-name',
          serialNumber: 'test-serial-number',
          systemUuid: 'test-system-uuid',
          systemSkuNumber: 'test-system-sku-number',
          systemAssettag: 'test-system-assettag',
          biosVendor: 'test-bios-vendor',
          biosVersion: 'test-bios-version',
          biosReleaseDate: 'test-bios-release-date',
          biosRomSize: 'test-bios-rom-size',
          biosRevision: 'test-bios-revision',
        } as ApiHardwareInfo,
      }),
    ]);

    const hardwareInfoHarnesses = await harness.hardwareInfoDetailsHarnesses();
    expect(hardwareInfoHarnesses).toHaveSize(1);
    const hardwareInfoHarness = hardwareInfoHarnesses[0];
    const table = await hardwareInfoHarness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toContain('Manufacturer');
    expect(await table.text()).toContain('test-system-manufacturer');
    expect(await table.text()).toContain('Family');
    expect(await table.text()).toContain('test-system-family');
    expect(await table.text()).toContain('Product Name');
    expect(await table.text()).toContain('test-system-product-name');
    expect(await table.text()).toContain('Serial Number');
    expect(await table.text()).toContain('test-serial-number');
    expect(await table.text()).toContain('UUID');
    expect(await table.text()).toContain('test-system-uuid');
    expect(await table.text()).toContain('SKU Number');
    expect(await table.text()).toContain('test-system-sku-number');
    expect(await table.text()).toContain('Asset Tag');
    expect(await table.text()).toContain('test-system-assettag');
    expect(await table.text()).toContain('BIOS Vendor');
    expect(await table.text()).toContain('test-bios-vendor');
    expect(await table.text()).toContain('BIOS Version');
    expect(await table.text()).toContain('test-bios-version');
    expect(await table.text()).toContain('BIOS Release Date');
    expect(await table.text()).toContain('test-bios-release-date');
    expect(await table.text()).toContain('BIOS ROM Size');
    expect(await table.text()).toContain('test-bios-rom-size');
    expect(await table.text()).toContain('BIOS Revision');
    expect(await table.text()).toContain('test-bios-revision');
  }));

  it('shows multiple file finder results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.HARDWARE_INFO,
        payload: {} as ApiHardwareInfo,
      }),
      newFlowResult({
        payloadType: PayloadType.HARDWARE_INFO,
        payload: {} as ApiHardwareInfo,
      }),
    ]);

    const hardwareInfoHarnesses = await harness.hardwareInfoDetailsHarnesses();
    expect(hardwareInfoHarnesses).toHaveSize(2);
  }));

  it('shows client id for hunt results', async () => {
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
  });

  it('does not show client id for flow results', async () => {
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
  });
});
