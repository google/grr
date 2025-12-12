import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {Process} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {ProcessTree, toTrees} from './process_tree';
import {ProcessTreeHarness} from './testing/process_tree_harness';

initTestEnvironment();

async function createComponent(processes: Process[]) {
  const fixture = TestBed.createComponent(ProcessTree);
  fixture.componentRef.setInput('processes', processes);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ProcessTreeHarness,
  );
  return {fixture, harness};
}

describe('Process Tree Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ProcessTree, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent([]);

    expect(fixture.componentInstance).toBeDefined();
  });

  it('displays a single process results', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        pid: 1111,
        cmdline: ['/foo', 'bar'],
        username: 'testuser',
      },
    ]);

    const tree = await harness.tree();
    const treeNodes = await tree.getNodes();
    expect(treeNodes.length).toBe(1);
    expect(await treeNodes[0].getText()).toContain('1111');
    expect(await treeNodes[0].getText()).toContain('/foo bar');
    expect(await treeNodes[0].getText()).toContain('testuser');
  }));

  it('displays several independent processes', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        pid: 1111,
        cmdline: ['cmd1'],
        username: 'FOO',
      },
      {
        pid: 2222,
        cmdline: ['cmd2'],
        username: 'BAR',
      },
    ]);

    const tree = await harness.tree();
    const treeNodes = await tree.getNodes();
    expect(treeNodes.length).toBe(2);
    expect(await treeNodes[0].getText()).toContain('1111');
    expect(await treeNodes[0].getText()).toContain('cmd1');
    expect(await treeNodes[0].getText()).toContain('FOO');
    expect(await treeNodes[1].getText()).toContain('2222');
    expect(await treeNodes[1].getText()).toContain('cmd2');
    expect(await treeNodes[1].getText()).toContain('BAR');
  }));

  it('initially displays only root processes', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        pid: 1,
      },
      {
        pid: 12,
        ppid: 1,
      },
    ]);

    const tree = await harness.tree();
    const treeNodes = await tree.getNodes();
    expect(treeNodes.length).toBe(1);
    expect(await treeNodes[0].getText()).toContain('1');
    expect(await treeNodes[0].getText()).not.toContain('12');
  }));

  it('displays nested processes after expanding', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        pid: 1,
      },
      {
        pid: 12,
        ppid: 1,
      },
      {
        pid: 123,
        ppid: 12,
      },
      {
        pid: 124,
        ppid: 12,
      },
    ]);
    const tree = await harness.tree();

    const firstGroup = (await tree.getNodes({text: '1'}))[0];
    await firstGroup.expand();
    const secondGroup = (await tree.getNodes({text: '12'}))[0];
    await secondGroup.expand();

    const expandedNodes = await tree.getNodes();
    expect(expandedNodes.length).toBe(4);
    expect(await expandedNodes[0].getText()).toContain('1');
    expect(await expandedNodes[1].getText()).toContain('12');
    expect(await expandedNodes[2].getText()).toContain('123');
    expect(await expandedNodes[3].getText()).toContain('124');
  }));

  it('displays an error message when there are orphaned processes', fakeAsync(async () => {
    const {harness} = await createComponent([
      {
        pid: 1,
      },
      {
        pid: 2,
        ppid: 4,
      },
      {
        pid: 3,
        ppid: 2,
      },
      {
        pid: 4,
        ppid: 3,
      },
    ]);

    const errorMessage = await harness.errorMessage();
    expect(errorMessage).toBeDefined();
    expect(await errorMessage!.getMessage()).toContain(
      'There are cycles in the process tree',
    );
  }));

  describe('toTrees', () => {
    it('converts a single process to a tree', () => {
      const processes = [
        {
          pid: 1,
        },
      ];

      const trees = toTrees(processes);

      const {rootNodes, detectedCycles} = trees;
      expect(rootNodes).toHaveSize(1);
      expect(rootNodes[0].pid).toBe(1);
      expect(rootNodes[0].children).toHaveSize(0);
      expect(detectedCycles).toBeFalse();
    });

    it('converts a process tree to a tree', () => {
      const processes = [
        {
          pid: 1,
        },
        {
          pid: 2,
          ppid: 1,
        },
        {
          pid: 3,
          ppid: 1,
        },
        {
          pid: 4,
          ppid: 3,
        },
        {
          pid: 5,
          ppid: 3,
        },
      ];

      const trees = toTrees(processes);

      const {rootNodes, detectedCycles} = trees;
      expect(rootNodes).toHaveSize(1);
      expect(rootNodes[0].pid).toBe(1);
      expect(rootNodes[0].children).toHaveSize(2);
      expect(rootNodes[0].children[0].pid).toBe(2);
      expect(rootNodes[0].children[0].children).toHaveSize(0);
      expect(rootNodes[0].children[1].pid).toBe(3);
      expect(rootNodes[0].children[1].children).toHaveSize(2);
      expect(rootNodes[0].children[1].children[0].pid).toBe(4);
      expect(rootNodes[0].children[1].children[0].children).toHaveSize(0);
      expect(rootNodes[0].children[1].children[1].pid).toBe(5);
      expect(rootNodes[0].children[1].children[1].children).toHaveSize(0);
      expect(detectedCycles).toBeFalse();
    });

    it('ignores a missing parent process', () => {
      const processes = [
        {
          pid: 1,
        },
        {
          pid: 2,
          ppid: 3,
        },
      ];

      const trees = toTrees(processes);

      const {rootNodes, detectedCycles} = trees;

      expect(detectedCycles).toBeFalse();
      expect(rootNodes).toHaveSize(2);
      expect(rootNodes[0].pid).toBe(1);
      expect(rootNodes[0].children).toHaveSize(0);
      expect(rootNodes[1].pid).toBe(2);
      expect(rootNodes[1].children).toHaveSize(0);
    });

    it('detects a cyclic tree', () => {
      const processes = [
        {
          pid: 1,
        },
        {
          pid: 2,
          ppid: 4,
        },
        {
          pid: 3,
          ppid: 2,
        },
        {
          pid: 4,
          ppid: 3,
        },
      ];

      const trees = toTrees(processes);

      const {rootNodes, detectedCycles} = trees;
      expect(detectedCycles).toBeTrue();
      expect(rootNodes).toHaveSize(1);
      expect(rootNodes[0].pid).toBe(1);
      expect(rootNodes[0].children).toHaveSize(0);
    });
  });
});
