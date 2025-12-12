import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CloudInstance,
  CloudInstanceInstanceType,
} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {CloudInstanceDetails} from './cloud_instance_details';
import {CloudInstanceDetailsHarness} from './testing/cloud_instance_details_harness';

initTestEnvironment();

async function createComponent(cloudInstance: CloudInstance | undefined) {
  const fixture = TestBed.createComponent(CloudInstanceDetails);
  fixture.componentRef.setInput('cloudInstance', cloudInstance);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CloudInstanceDetailsHarness,
  );

  return {fixture, harness};
}

describe('Cloud Instance Details Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CloudInstanceDetails, NoopAnimationsModule],
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

  it('shows a complete google cloud instance', async () => {
    const {harness} = await createComponent({
      cloudType: CloudInstanceInstanceType.GOOGLE,
      google: {
        uniqueId: '1234567890',
        zone: 'google-zone',
        projectId: 'google-test-project',
        instanceId: 'google-1234567890',
        hostname: 'google.host',
        machineType: 'google-machine-type',
      },
    });

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toContain('Type');
    expect(await table.text()).toContain('GOOGLE');
    expect(await table.text()).toContain('Unique ID');
    expect(await table.text()).toContain('1234567890');
    expect(await table.text()).toContain('Zone');
    expect(await table.text()).toContain('google-zone');
    expect(await table.text()).toContain('Project');
    expect(await table.text()).toContain('google-test-project');
    expect(await table.text()).toContain('Instance');
    expect(await table.text()).toContain('google-1234567890');
    expect(await table.text()).toContain('Hostname');
    expect(await table.text()).toContain('google.host');
    expect(await table.text()).toContain('Machine Type');
    expect(await table.text()).toContain('google-machine-type');
  });

  it('shows a complete amazon instance', async () => {
    const {harness} = await createComponent({
      cloudType: CloudInstanceInstanceType.AMAZON,
      amazon: {
        instanceId: 'aws-1234567890',
        hostname: 'aws.host',
        publicHostname: 'aws-instance.public.com',
        amiId: 'amid-1234567890',
        instanceType: 'aws-instance',
      },
    });

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toContain('Type');
    expect(await table.text()).toContain('AMAZON');
    expect(await table.text()).toContain('Instance');
    expect(await table.text()).toContain('aws-1234567890');
    expect(await table.text()).toContain('Hostname');
    expect(await table.text()).toContain('aws.host');
    expect(await table.text()).toContain('Public Hostname');
    expect(await table.text()).toContain('aws-instance.public.com');
    expect(await table.text()).toContain('AMI');
    expect(await table.text()).toContain('amid-1234567890');
    expect(await table.text()).toContain('Instance Type');
    expect(await table.text()).toContain('aws-instance');
  });
});
