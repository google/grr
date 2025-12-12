import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatTreeModule} from '@angular/material/tree';

import {Process} from '../../../../lib/api/api_interfaces';
import {createOptionalDate} from '../../../../lib/api/translation/primitive';
import {ErrorMessage} from '../../error_message';
import {Timestamp} from '../../timestamp';

interface ProcessTreeData {
  readonly rootNodes: ProcessNode[];
  readonly detectedCycles: boolean;
}

interface ProcessNode extends Process {
  readonly pid: number;
  readonly date?: Date;
  readonly children: ProcessNode[];
}

function toNode(process: Process): ProcessNode {
  return {
    ...process,
    pid: process.pid!,
    date: createOptionalDate(process.ctime),
    children: [],
  };
}

/**
 * Converts a list of processes to a list of process trees. The function groups
 * processes by their parent process ID and creates a tree structure. If there
 * are orphaned processes, the function throws an error.
 */
export function toTrees(processes: readonly Process[]): ProcessTreeData {
  const rootNodes = new Set(processes.map(toNode));
  const childNodes = new Array<number>();

  const nodeMap = new Map(
    Array.from(rootNodes.values(), (node) => [node.pid, node]),
  );

  for (const node of nodeMap.values()) {
    if (node.ppid === undefined) {
      continue;
    }
    const parent = nodeMap.get(node.ppid);
    if (parent === undefined) {
      continue;
    }
    parent.children.push(node);
    childNodes.push(node.pid);
    rootNodes.delete(node);
  }

  const detectedCycles = detectCycles(nodeMap);

  return {rootNodes: Array.from(rootNodes), detectedCycles};
}

/**
 * Detects cycles in a process tree.
 *
 * The function checks if there are any processes that are not connected to any
 * root processes.
 */
export function detectCycles(processMap: Map<number, ProcessNode>): boolean {
  const visited = new Set<number>();

  for (const node of processMap.values()) {
    let current = node;
    if (current.ppid === undefined) {
      continue;
    }

    if (visited.has(current.pid)) {
      continue;
    }

    const ancestors = new Set<number>();
    ancestors.add(current.pid);
    while (current.ppid !== undefined) {
      if (ancestors.has(current.ppid)) {
        return true;
      }
      ancestors.add(current.ppid);
      current = processMap.get(current.ppid)!;
      // When listing processes, it is possible that a process with its parent
      // process id is captured, but as listing processes takes a while the
      // parent process might have terminated in the meantime, so it is not
      // captured and `current` here is undefined.
      if (current === undefined) {
        break;
      }
    }
    ancestors.forEach((pid) => {
      visited.add(pid);
    });
  }
  return false;
}

/** Component to show a tree-view of operating system processes. */
@Component({
  selector: 'process-tree',
  templateUrl: './process_tree.ng.html',
  styleUrls: ['./process_tree.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    ErrorMessage,
    MatButtonModule,
    MatIconModule,
    MatTreeModule,
    Timestamp,
  ],
})
export class ProcessTree {
  readonly processes = input.required<ProcessTreeData, readonly Process[]>({
    transform: toTrees,
  });

  childrenAccessor = (node: ProcessNode) => node.children ?? [];

  hasChild = (_: number, node: ProcessNode) =>
    !!node.children && node.children.length > 0;
}
