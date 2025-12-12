import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CloudInstance as ApiCloudInstance,
  CloudInstanceInstanceType,
} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {CollectCloudVmMetadataResults} from './collect_cloud_vm_metadata_results';
import {CollectCloudVmMetadataResultsHarness} from './testing/collect_cloud_vm_metadata_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(CollectCloudVmMetadataResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectCloudVmMetadataResultsHarness,
  );

  return {fixture, harness};
}

describe('Collect Cloud VM Metadata Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectCloudVmMetadataResults, NoopAnimationsModule],
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
        payloadType: PayloadType.COLLECT_CLOUD_VM_METADATA_RESULT,
        payload: {
          cloudType: CloudInstanceInstanceType.GOOGLE,
          google: {
            uniqueId: 'test-unique-id',
            zone: 'test-zone',
            projectId: 'test-project-id',
            instanceId: 'test-instance-id',
            hostname: 'test-hostname',
            machineType: 'test-machine-type',
          },
        } as ApiCloudInstance,
      }),
    ]);

    const cloudInstanceDetailsHarnesses =
      await harness.cloudInstanceDetailsHarnesses();
    expect(cloudInstanceDetailsHarnesses).toHaveSize(1);
    const cloudInstanceDetailsHarness = cloudInstanceDetailsHarnesses[0];
    const table = await cloudInstanceDetailsHarness.table();
    expect(table).toBeDefined();
    expect(await table.text()).toContain('Unique ID');
    expect(await table.text()).toContain('test-unique-id');
    expect(await table.text()).toContain('Zone');
    expect(await table.text()).toContain('test-zone');
    expect(await table.text()).toContain('Project');
    expect(await table.text()).toContain('test-project-id');
    expect(await table.text()).toContain('Instance');
    expect(await table.text()).toContain('test-instance-id');
    expect(await table.text()).toContain('Hostname');
    expect(await table.text()).toContain('test-hostname');
    expect(await table.text()).toContain('Machine Type');
    expect(await table.text()).toContain('test-machine-type');
  }));

  it('shows multiple file finder results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.COLLECT_CLOUD_VM_METADATA_RESULT,
        payload: {} as ApiCloudInstance,
      }),
      newFlowResult({
        payloadType: PayloadType.COLLECT_CLOUD_VM_METADATA_RESULT,
        payload: {} as ApiCloudInstance,
      }),
    ]);

    const cloudInstanceDetailsHarnesses =
      await harness.cloudInstanceDetailsHarnesses();
    expect(cloudInstanceDetailsHarnesses).toHaveSize(2);
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
