import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HardwareInfo} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {HardwareInfoDetails} from './hardware_info_details';
import {HardwareInfoDetailsHarness} from './testing/hardware_info_details_harness';

initTestEnvironment();

async function createComponent(hardwareInfo: HardwareInfo | undefined) {
  const fixture = TestBed.createComponent(HardwareInfoDetails);
  fixture.componentRef.setInput('hardwareInfo', hardwareInfo);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    HardwareInfoDetailsHarness,
  );

  return {fixture, harness};
}

describe('Hardware Info Details Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HardwareInfoDetails, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent(undefined);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows an empty table if there are no results', async () => {
    const {harness} = await createComponent(undefined);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toBe('');
  });

  it('shows a complete hardware info', async () => {
    const {harness} = await createComponent({
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
    });

    const table = await harness.table();
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
  });
});
