import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ListContainersFlowResult as ApiListContainersFlowResult} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {ListContainersFlowResults} from './list_containers_flow_results';
import {ListContainersFlowResultsHarness} from './testing/list_containers_flow_results_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(ListContainersFlowResults);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ListContainersFlowResultsHarness,
  );

  return {fixture, harness};
}

describe('List Containers Flow Results Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ListContainersFlowResults, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows no table if there are no results', fakeAsync(async () => {
    const {harness} = await createComponent([]);

    expect(await harness.table()).toBeNull();
  }));

  it('shows a single container', fakeAsync(async () => {
    const container: ApiListContainersFlowResult = {
      containers: [
        {
          containerId: 'container-id',
          imageName: 'image-name',
          command: 'command',
          createdAt: '1600000000000000',
          status: 'status',
          ports: ['port1', 'port2'],
          names: ['name1', 'name2'],
          localVolumes: 'local-volumes',
          mounts: ['mount1', 'mount2'],
          networks: ['network1', 'network2'],
          runningSince: '999000',
        },
      ],
    };
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.LIST_CONTAINERS_FLOW_RESULT,
        payload: container,
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(1);
    expect(await harness.getCellText(0, 'containerId')).toContain(
      'container-id',
    );
    expect(await harness.getCellText(0, 'imageName')).toContain('image-name');
    expect(await harness.getCellText(0, 'command')).toEqual('command');
    expect(await harness.getCellText(0, 'createdAt')).toContain(
      '2020-09-13 12:26:40 UTC',
    );
    expect(await harness.getCellText(0, 'status')).toEqual('status');
    expect(await harness.getCellText(0, 'ports')).toEqual('port1, port2');
    expect(await harness.getCellText(0, 'names')).toEqual('name1, name2');
    expect(await harness.getCellText(0, 'localVolumes')).toEqual(
      'local-volumes',
    );
    expect(await harness.getCellText(0, 'mounts')).toEqual('mount1, mount2');
    expect(await harness.getCellText(0, 'networks')).toEqual(
      'network1, network2',
    );
  }));

  it('shows multiple flow results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.LIST_CONTAINERS_FLOW_RESULT,
        payload: {
          containers: [
            {
              containerId: 'container-id',
            },
          ],
        },
      }),
      newFlowResult({
        payloadType: PayloadType.LIST_CONTAINERS_FLOW_RESULT,
        payload: {
          containers: [
            {
              containerId: 'container-id-2',
            },
          ],
        },
      }),
    ]);

    const table = await harness.table();
    expect(table).toBeDefined();
    expect(await table!.getRows()).toHaveSize(2);
  }));

  it('shows client id for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.LIST_CONTAINERS_FLOW_RESULT,
        payload: {
          containers: [
            {
              containerId: 'container-id',
            },
          ],
        },
      }),
    ]);

    expect(await harness.getCellText(0, 'clientId')).toContain('C.1234');
  }));
});
