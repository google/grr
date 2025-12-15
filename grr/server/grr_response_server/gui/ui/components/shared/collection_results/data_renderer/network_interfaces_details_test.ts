import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';

import {initTestEnvironment} from '../../../../testing';
import {NetworkInterfacesDetails} from './network_interfaces_details';
import {NetworkInterfacesDetailsHarness} from './testing/network_interfaces_details_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(NetworkInterfacesDetails);
  // Set the default value here as the input is required.
  fixture.componentRef.setInput('interfaces', []);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    NetworkInterfacesDetailsHarness,
  );
  return {fixture, harness};
}

describe('Network Interfaces Details Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NetworkInterfacesDetails],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('shows `None` if there are no network interfaces', async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('interfaces', []);
    expect(await harness.hasNoneText()).toBeTrue();
    expect(await harness.numTables()).toBe(0);
  });

  it('shows all details of one network interface', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('interfaces', [
      {
        macAddress: 'my:mac:address',
        interfaceName: 'test-network-interface',
        addresses: [
          {
            addressType: 'custom-address-type',
            ipAddress: '1.2.3.4',
          },
          {
            addressType: 'another-address-type',
            ipAddress: '9.8.7.6',
          },
        ],
      },
    ]);
    tick();
    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(1);
    expect(await harness.numRows()).toBe(3);
    const rowTexts = await harness.getRowTexts();

    expect(rowTexts[0]).toContain('Name');
    expect(rowTexts[0]).toContain('test-network-interface');

    expect(rowTexts[1]).toContain('MAC Address');
    expect(rowTexts[1]).toContain('my:mac:address');

    expect(rowTexts[2]).toContain('IP Addresses');
    expect(rowTexts[2]).toContain('1.2.3.4');
    expect(rowTexts[2]).toContain('9.8.7.6');
  }));

  it('renders multiple network interfaces', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('interfaces', [
      {macAddress: 'my:mac:address', addresses: []},
      {macAddress: 'another:mac:address', addresses: []},
      {macAddress: 'yet:another:mac:address', addresses: []},
    ]);
    tick();
    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(3);
    expect(await harness.numRows()).toBe(9);
  }));
});
