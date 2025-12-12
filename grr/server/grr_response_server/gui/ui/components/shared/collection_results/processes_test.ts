import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {Processes} from './processes';
import {ProcessesHarness} from './testing/processes_harness';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(Processes);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ProcessesHarness,
  );

  return {fixture, harness};
}

describe('Processes Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [Processes, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('displays process tree', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.PROCESS,
        payload: {pid: 0, cmdline: ['/foo', 'bar']},
      }),
    ]);

    const processTrees = await harness.processTrees();
    expect(processTrees).toHaveSize(1);
    const processTree = processTrees[0];
    const tree = await processTree.tree();
    const treeNodes = await tree.getNodes();
    expect(treeNodes.length).toBe(1);
    expect(await treeNodes[0].getText()).toContain('0');
    expect(await treeNodes[0].getText()).toContain('/foo bar');
  }));

  it('shows client id for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.PROCESS,
        payload: {pid: 0, cmdline: ['/foo', 'bar']},
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(1);
    expect(await clientIds[0].text()).toContain('Client ID: C.1234');
  }));

  it('shows separate process trees for multiple clients', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.PROCESS,
        payload: {pid: 0, cmdline: ['/foo', 'bar']},
      }),
      newHuntResult({
        clientId: 'C.5678',
        payloadType: PayloadType.PROCESS,
        payload: {pid: 100, cmdline: ['/foo', 'baz']},
      }),
    ]);

    const clientIds = await harness.clientIds();
    expect(clientIds).toHaveSize(2);
    expect(await clientIds[0].text()).toContain('Client ID: C.1234');
    expect(await clientIds[1].text()).toContain('Client ID: C.5678');
    const processTrees = await harness.processTrees();
    expect(processTrees).toHaveSize(2);
    const processTree1 = processTrees[0];
    const tree1 = await processTree1.tree();
    const treeNodes1 = await tree1.getNodes();
    expect(treeNodes1.length).toBe(1);
    expect(await treeNodes1[0].getText()).toContain('0');
    expect(await treeNodes1[0].getText()).toContain('/foo bar');
    const processTree2 = processTrees[1];
    const tree2 = await processTree2.tree();
    const treeNodes2 = await tree2.getNodes();
    expect(treeNodes2.length).toBe(1);
    expect(await treeNodes2[0].getText()).toContain('100');
    expect(await treeNodes2[0].getText()).toContain('/foo baz');
  }));
});
