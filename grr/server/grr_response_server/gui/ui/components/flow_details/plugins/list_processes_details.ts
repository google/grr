import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Observable} from 'rxjs';
import {map} from 'rxjs/operators';

import {Process} from '../../../lib/api/api_interfaces';

import {Plugin} from './plugin';

interface ProcessNode extends Process {
  readonly pid: number;
  readonly children: ProcessNode[];
}

function newNode(process: Process): ProcessNode {
  return {
    ...process,
    pid: process.pid!,
    children: [],
  };
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

  readonly processes$: Observable<ProcessNode[]> = this.flowListEntry$.pipe(
      map(fle => fle.resultSets.flatMap(
              rs => rs.items.map(item => item.payload as Process))),
      map(toTrees),
  );

  onShowClicked() {
    this.showResults = true;
    this.queryFlowResults({
      offset: 0,
      count: INITIAL_RESULT_COUNT,
    });
  }
}
