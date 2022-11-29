import * as DeepDiffMod from 'deep-diff';
const DeepDiff = (DeepDiffMod as any).default;

import {Client} from '../lib/models/client';

// Use proper typing once @types/deep_diff has been upgraded.
// tslint:disable-next-line:no-any
type Diff<T> = any;
const {diff} = DeepDiff;

/** Client Version */
export interface ClientVersion {
  client: Client;
  changes: ReadonlyArray<string>;
}

/**
 * A map containing the relevant entries (as keys) taken into consideration
 * when computing the differences between client snapshots.
 * If the property is nested, the path to it should be concatenated using the
 * "." symbol (e.g. "knowledgeBase.fqdn"). The items in the path must be the raw
 * property names.
 * A human readable label must be provided (as value) describing the entry to be
 * shown in the UI.
 */
const RELEVANT_ENTRIES_LABEL_MAP = new Map([
  ['clientId', 'Client ID'],
  ['labels', 'Label'],
  ['osInfo', 'OS Info'],
  ['osInfo.system', 'System type'],
  ['osInfo.release', 'OS release'],
  ['osInfo.version', 'OS version'],
  ['osInfo.kernel', 'Kernel version'],
  ['osInfo.installDate', 'OS install date'],
  ['osInfo.machine', 'System machine type'],
  ['memorySize', 'Memory size'],
  ['knowledgeBase.fqdn', 'FQDN'],
  ['knowledgeBase.osMajorVersion', 'OS major version'],
  ['knowledgeBase.osMinorVersion', 'OS minor version'],
  ['users', 'User'],
  ['users.username', 'Username'],
  ['users.fullName', 'User full name'],
  ['users.lastLogon', 'User last logon'],
  ['users.homedir', 'User home directory'],
  ['users.uid', 'User UID'],
  ['users.gid', 'User GID'],
  ['users.shell', 'User shell'],
  ['networkInterfaces', 'Network interface'],
  ['networkInterfaces.interfaceName', 'Network interface name'],
  ['networkInterfaces.macAddress', 'MAC address'],
  ['networkInterfaces.addresses', 'Network address'],
  ['networkInterfaces.addresses.ipAddress', 'IP address'],
  ['volumes', 'Volume'],
  ['volumes.windowsDetails', 'Volume details'],
  ['volumes.windowsDetails.driveLetter', 'Volume letter'],
  ['volumes.windowsDetails.attributes', 'Volume attributes'],
  ['volumes.windowsDetails.driveType', 'Volume type'],
  ['volumes.unixDetails', 'Volume details'],
  ['volumes.unixDetails.mountPoint', 'Volume mount point'],
  ['volumes.unixDetails.mountOptions', 'Volume mount options'],
  ['volumes.name', 'Volume name'],
  ['volumes.devicePath', 'Volume device path'],
  ['volumes.fileSystemType', 'Volume filesystem type'],
  ['volumes.totalSize', 'Volume size'],
  ['volumes.freeSpace', 'Volume free space'],
  ['volumes.bytesPerSector', 'Volume bytes per sector'],
  ['volumes.creationTime', 'Volume creation time'],
  ['agentInfo.clientName', 'GRR agent name'],
  ['agentInfo.clientVersion', 'GRR agent version'],
  ['agentInfo.buildTime', 'GRR agent build time'],
  ['agentInfo.clientBinaryName', 'GRR agent binary name'],
  ['agentInfo.clientDescription', 'GRR agent description'],
]);

/**
 * Classifies a Diff item into one of the categories added, deleted and updated
 * provided as Map objects. The classification adds identical changes into the
 * same map entry and increments the counter for that change.
 */
function classifyDiffItem(
    diffItem: Diff<Client>, added: Map<string, number>,
    deleted: Map<string, number>, updated: Map<string, number>) {
  if (diffItem.path === undefined) return;
  const path = getStringsJoinedPath(diffItem.path);

  const label = RELEVANT_ENTRIES_LABEL_MAP.get(path);
  if (label === undefined) return;

  switch (diffItem.kind) {
    case 'N':
      added.set(label, (added.get(label) ?? 0) + 1);
      break;
    case 'D':
      deleted.set(label, (deleted.get(label) ?? 0) + 1);
      break;
    case 'A':
      classifyDiffItem(
          {...diffItem.item, path: diffItem.item.path ?? diffItem.path}, added,
          deleted, updated);
      break;
    default:
      updated.set(label, (updated.get(label) ?? 0) + 1);
  }
}

/**
 * Creates the descriptions for the aggregated changes
 * @param changesMap Map containing changes of the same
 *     type (add / delete / update)
 * @param changeKeyword A lowercase keyword to specify the change type (e.g.
 *     "added")
 */
function getChangeDescriptions(
    changesMap: Map<string, number>,
    changeKeyword: string): ReadonlyArray<string> {
  const changeDescriptions: string[] = [];

  changesMap.forEach((occurrences, label) => {
    if (occurrences === 1) {
      changeDescriptions.push(`${label} ${changeKeyword}`);
    } else {
      changeDescriptions.push(
          `${occurrences} ${label} entries ${changeKeyword}`);
    }
  });

  return changeDescriptions;
}

function getNumEntriesChanged(changesMap: Map<string, number>): number {
  let numEntriesChanged = 0;

  changesMap.forEach(entries => {
    numEntriesChanged += entries;
  });

  return numEntriesChanged;
}

/**
 * Returns the number of entries changed and a list of the aggregated changes
 * descriptions (e.g. "2 users added")
 */
function aggregateDiffs(differences?: ReadonlyArray<Diff<Client>>):
    // tslint:disable-next-line:array-type
    [number, ReadonlyArray<string>] {
  if (differences === undefined) {
    return [0, []];
  }

  const added = new Map<string, number>();
  const deleted = new Map<string, number>();
  const updated = new Map<string, number>();
  const changesDescriptions: string[] = [];
  let numEntriesChanged = 0;

  differences.forEach((item) => {
    classifyDiffItem(item, added, deleted, updated);
  });

  changesDescriptions.push(...getChangeDescriptions(added, 'added'));
  changesDescriptions.push(...getChangeDescriptions(deleted, 'deleted'));
  changesDescriptions.push(...getChangeDescriptions(updated, 'updated'));

  numEntriesChanged = getNumEntriesChanged(added);
  numEntriesChanged += getNumEntriesChanged(deleted);
  numEntriesChanged += getNumEntriesChanged(updated);

  return [numEntriesChanged, changesDescriptions];
}

/**
 * Returns an array with descriptions of the changes between the two client
 * snapshots provided.
 * When there are no relevant changes, the array will be empty.
 */
function getSnapshotChanges(
    current: Client, old?: Client): ReadonlyArray<string> {
  if (old === undefined) {
    return ['Client first seen'];
  }

  const diffDescriptions = aggregateDiffs(diff(old, current));

  if (diffDescriptions[1].length > 3) {
    return [`${diffDescriptions[0]} new changes`];
  }

  return diffDescriptions[1];
}

/**
 * Converts an array of snapshots into an array of client versions also
 * containing the changes between versions.
 * @param clientSnapshots an array of chronologically reverse ordered client
 *     snapshots
 */
export function getClientVersions(clientSnapshots: ReadonlyArray<Client>):
    ClientVersion[] {
  const clientChanges: ClientVersion[] = [];

  for (let i = 0; i < clientSnapshots.length; i++) {
    const clientChange =
        getSnapshotChanges(clientSnapshots[i], clientSnapshots[i + 1]);
    clientChanges.push({
      client: clientSnapshots[i],
      changes: clientChange,
    });
  }

  return clientChanges;
}

/**
 * Returns the first string elements in the path.
 *
 * A path may contain non-string elements, like [0,1,..n] for array access,
 * because deep-diff can find differences between individual elements of an
 * array. Unfortunately, showing detailed versions of array individual elements
 * is not currently supported by us in the UI. In case the path contains a
 * number, it means that the algorithm found a difference within an array, so we
 * truncate it right there to obtain only the path to the array object. That way
 * we can gather all the changes within the array under a bigger umbrella.
 */
// tslint:disable-next-line:no-any Provided by deep-diff typing.
function getFirstStringsJoinedPath(path: any[]): string {
  const tokens: string[] = [];

  for (let i = 0; i < path.length; i++) {
    if (typeof path[i] !== 'string') break;
    tokens.push(path[i]);
  }

  return tokens.join('.');
}

// tslint:disable-next-line:no-any
function getStringsJoinedPath(path: any[]): string {
  return path.filter(val => typeof val === 'string').join('.');
}

function pairwise<T>(arr: ReadonlyArray<T>): ReadonlyArray<[T, T]> {
  const pairwiseArray: Array<[T, T]> = [];
  for (let i = 0; i < arr.length - 1; i++) {
    pairwiseArray.push([arr[i], arr[i + 1]]);
  }

  return pairwiseArray;
}

function getPathsOfChangedEntries(differences: ReadonlyArray<Diff<Client>>):
    ReadonlyArray<string> {
  const changedPaths = new Set<string>();

  differences.filter(diffItem => diffItem.path !== undefined)
      .filter(
          diffItem => RELEVANT_ENTRIES_LABEL_MAP.has(
              getStringsJoinedPath(diffItem.path)))
      .map(diffItem => getFirstStringsJoinedPath(diffItem.path))
      .forEach(path => {
        changedPaths.add(path);
      });

  return Array.from(changedPaths);
}

/**
 * Returns relevant entry paths mapped to the client snapshots in which the
 * changes were introduced.
 *
 * The clients are reverse chronologically ordered. A property path may not be
 * inside the map if no changes were applied to it since it's creation
 *
 * @param clientSnapshots an array of chronologically reverse ordered client
 *     snapshots
 */
export function getClientEntriesChanged(clientSnapshots: ReadonlyArray<Client>):
    Map<string, ReadonlyArray<Client>> {
  const clientChangedEntries = new Map<string, Client[]>();

  pairwise(clientSnapshots).forEach(([newerClient, olderClient]) => {
    const differences = diff(olderClient, newerClient);
    if (differences === undefined) return;

    const paths = getPathsOfChangedEntries(differences);

    paths.forEach(path => {
      clientChangedEntries.set(
          path, [...clientChangedEntries.get(path) ?? [], newerClient]);
    });
  });

  // Add the first client snapshot, as a point of reference
  clientChangedEntries.forEach(value => {
    value.push(clientSnapshots[clientSnapshots.length - 1]);
  });

  return clientChangedEntries;
}
