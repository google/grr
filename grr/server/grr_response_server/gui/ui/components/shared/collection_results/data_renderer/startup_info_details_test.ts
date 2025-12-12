import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {StartupInfo} from '../../../../lib/models/client';
import {initTestEnvironment} from '../../../../testing';
import {StartupInfoDetails} from './startup_info_details';
import {StartupInfoDetailsHarness} from './testing/startup_info_details_harness';

initTestEnvironment();

async function createComponent(startupInfo: StartupInfo | undefined) {
  const fixture = TestBed.createComponent(StartupInfoDetails);
  fixture.componentRef.setInput('startupInfo', startupInfo);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    StartupInfoDetailsHarness,
  );

  return {fixture, harness};
}

describe('Startup Info Details Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [StartupInfoDetails, NoopAnimationsModule],
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

  it('shows a complete startup info', fakeAsync(async () => {
    const {harness} = await createComponent({
      bootTime: new Date('2024-01-01T00:00:00Z'),
      clientInfo: {
        clientName: 'test-client-name',
        clientVersion: 123,
        revision: BigInt(456),
        buildTime: new Date('2025-01-01T00:00:00Z'),
        clientBinaryName: 'test-client-binary-name',
        clientDescription: 'test-client-description',
        sandboxSupport: true,
        timelineBtimeSupport: true,
      },
    });

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toContain('Boot Time');
    expect(await table.text()).toContain('2024-01-01 00:00:00');
    expect(await table.text()).toContain('Client Name');
    expect(await table.text()).toContain('test-client-name');
    expect(await table.text()).toContain('Client Version');
    expect(await table.text()).toContain('123');
    expect(await table.text()).toContain('Build Time');
    expect(await table.text()).toContain('2025-01-01 00:00:00');
    expect(await table.text()).toContain('Binary Name');
    expect(await table.text()).toContain('test-client-binary-name');
    expect(await table.text()).toContain('Description');
    expect(await table.text()).toContain('test-client-description');
    expect(await table.text()).toContain('Capabilities');
    expect(await table.text()).toContain('Sandboxing supported');
    expect(await table.text()).toContain(
      'Btime field in Timeline flow supported',
    );
  }));
});
