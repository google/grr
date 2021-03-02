import {NestedTreeControl} from '@angular/cdk/tree';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {MatTreeNestedDataSource} from '@angular/material/tree';
import {map, takeUntil, takeWhile} from 'rxjs/operators';

import {Process} from '../../../lib/api/api_interfaces';
import {createOptionalDate} from '../../../lib/api_translation/primitive';
import {FlowListEntry} from '../../../lib/models/flow';

import {Plugin} from './plugin';


interface ProcessNode extends Process {
  readonly pid: number;
  readonly date?: Date;
  readonly children: ProcessNode[];
}

function newNode(process: Process): ProcessNode {
  return {
    ...process,
    pid: process.pid!,
    date: createOptionalDate(process.ctime),
    children: [],
  };
}

function asProcess(data: unknown): Process {
  const process = data as Process;

  if (process.pid === undefined) {
    throw new Error(`"Expected Process with pid, received ${data}.`);
  }

  return process;
}

function getResults<T>(
    fle: FlowListEntry, mapper: (result: unknown) => T): T[] {
  return fle.resultSets.flatMap(
      rs => rs.items.map(item => mapper(item.payload)));
}

function toTrees(processes: Process[]): ProcessNode[] {
  const rootNodes = new Set(processes.map(newNode));
  const nodes = new Map(Array.from(rootNodes.values()).map(p => ([p.pid, p])));

  for (const node of nodes.values()) {
    if (node.ppid === undefined) {
      continue;
    }

    const parent = nodes.get(node.ppid);
    if (parent === undefined) {
      continue;
    }

    parent.children.push(node);
    rootNodes.delete(node);
  }

  return Array.from(rootNodes);
}

const INITIAL_RESULT_COUNT = 1000;

/** Fallback component when flow results have not been implemented. */
@Component({
  templateUrl: './list_processes_details.ng.html',
  styleUrls: ['./list_processes_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ListProcessesDetails extends Plugin {
  showResults = false;

  readonly treeControl = new NestedTreeControl<ProcessNode, number>(
      node => node.children, {trackBy: (node) => node.pid});

  readonly dataSource = new MatTreeNestedDataSource<ProcessNode>();

  constructor() {
    super();

    this.flowListEntry$
        .pipe(
            map(fle => getResults(fle, asProcess)),
            map(toTrees),
            takeWhile((nodes) => nodes.length === 0, true),
            takeUntil(this.unsubscribe$),
            )
        .subscribe(nodes => {
          this.dataSource.data = nodes;
        });
  }

  onShowClicked() {
    this.showResults = true;
    this.queryFlowResults({
      offset: 0,
      count: INITIAL_RESULT_COUNT,
    });
  }

  hasChild(index: number, process: ProcessNode): boolean {
    return process.children.length > 0;
  }
}
