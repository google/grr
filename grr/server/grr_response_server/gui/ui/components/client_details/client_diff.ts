import {Client} from '@app/lib/models/client';
import {diff, Diff} from 'deep-diff';

interface ClientVersion {
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
  const path = diffItem.path?.filter(val => typeof val === 'string').join('.');
  if (path === undefined) return;

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
};

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

  changesMap.forEach((occurences, label) => {
    if (occurences === 1) {
      changeDescriptions.push(`One ${label} ${changeKeyword}`);
    } else {
      changeDescriptions.push(
          `${occurences} ${label} entries ${changeKeyword}`);
    }
  });

  return changeDescriptions;
};

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
function aggregateDiffs(differences?: Diff<Client>[]):
    [number, ReadonlyArray<string>] {
  if (differences === undefined) {
    return [0, []];
  }

  const added: Map<string, number> = new Map();
  const deleted: Map<string, number> = new Map();
  const updated: Map<string, number> = new Map();
  const changesDescriptions: string[] = [];
  let numEntriesChanged = 0;

  differences.forEach(
      (item) => classifyDiffItem(item, added, deleted, updated));

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
    return ['Client created'];
  }

  const diffDescriptions = aggregateDiffs(diff(old, current));

  if (diffDescriptions[1].length > 3) {
    return [`${diffDescriptions[0]} new changes`]
  }

  return diffDescriptions[1];
}

/**
 * Converts an array of snapshots into an array of client versions also
 * containing the changes between versions.
 * @param clientSnapshots an array of chronologically reverse ordered client
 *     snapshots
 */
export function getClientVersions(clientSnapshots: Client[]):
    ReadonlyArray<ClientVersion> {
  const clientChanges: ClientVersion[] = [];

  for (let i = 0; i < clientSnapshots.length; i++) {
    const clientChange =
        getSnapshotChanges(clientSnapshots[i], clientSnapshots[i + 1]);
    if (clientChange.length !== 0) {
      clientChanges.push({
        client: clientSnapshots[i],
        changes: clientChange,
      });
    }
  }

  return clientChanges;
}
