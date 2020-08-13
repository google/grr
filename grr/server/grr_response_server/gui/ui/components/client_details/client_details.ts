import {ChangeDetectionStrategy, Component, OnDestroy, OnInit} from '@angular/core';
import {ActivatedRoute} from '@angular/router';
import {Client} from '@app/lib/models/client';
import {diff, Diff} from 'deep-diff';
import {Subject} from 'rxjs';
import {filter, map, takeUntil} from 'rxjs/operators';

import {ClientPageFacade} from '../../store/client_page_facade';

interface ClientVersion {
  client: Client;
  changes: string[];
}

/**
 * Component displaying the details for a single Client.
 */
@Component({
  templateUrl: './client_details.ng.html',
  styleUrls: ['./client_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientDetails implements OnInit, OnDestroy {
  // Not static & private because is referenced in the template
  readonly INITIAL_NUM_USERS_SHOWN = 1;
  readonly INITIAL_NUM_INTERFACES_SHOWN = 3;
  readonly INITIAL_NUM_VOLUMES_SHOWN = 2;

  private static readonly ENTRY_LABEL_MAP = new Map([
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

  private readonly id$ = this.route.paramMap.pipe(
      map(params => params.get('id')),
      filter((id): id is string => id !== null));

  readonly client$ = this.clientPageFacade.selectedClient$;
  readonly clientVersions$ = this.clientPageFacade.selectedClientVersions$.pipe(
      map(snapshots => snapshots.reverse()),
      map(this.getClientVersions),
  );

  currentNumUsersShown = this.INITIAL_NUM_USERS_SHOWN;
  currentNumInterfacesShown = this.INITIAL_NUM_INTERFACES_SHOWN;
  currentNumVolumesShown = this.INITIAL_NUM_VOLUMES_SHOWN;

  private readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly route: ActivatedRoute,
      private readonly clientPageFacade: ClientPageFacade,
  ) {}

  ngOnInit() {
    this.id$.pipe(takeUntil(this.unsubscribe$)).subscribe(id => {
      this.clientPageFacade.selectClient(id);
    });
  }

  getAccordionButtonState(
      totalNumElements: number, currentMaxNumElementsShown: number,
      initialMaxNumElementsShown: number): string {
    if (totalNumElements > currentMaxNumElementsShown) {
      return 'show-more';
    } else if (totalNumElements <= initialMaxNumElementsShown) {
      return 'no-button';
    }
    return 'show-less';
  }

  /**
   * Returns the number of entries changed and a list of the aggregated changes
   * descriptions (e.g. "2 users added")
   */
  static getDiffDescriptions(diff?: Diff<Client>[]): [number, string[]] {
    if (diff === undefined) {
      return [0, []];
    }

    let added: Map<string, number> = new Map();
    let deleted: Map<string, number> = new Map();
    let updated: Map<string, number> = new Map();
    let diffDescriptions = [] as string[];
    let numChanges = 0;

    const classifyDiffItem = function(element: Diff<Client>) {
      const path =
          element.path?.filter(val => typeof val === 'string').join('.');
      if (path === undefined) return;

      const label = ClientDetails.ENTRY_LABEL_MAP.get(path);
      if (label === undefined) return;

      switch (element.kind) {
        case 'N':
          added.set(label, (added.get(label) ?? 0) + 1);
          break;
        case 'D':
          deleted.set(label, (deleted.get(label) ?? 0) + 1);
          break;
        case 'A':
          classifyDiffItem(
              {...element.item, path: element.item.path ?? element.path});
          break;
        default:
          updated.set(label, (updated.get(label) ?? 0) + 1);
      }
    };

    diff.forEach(classifyDiffItem);

    const addToChanges = function(
        classMap: Map<string, number>, changeKeyword: string) {
      classMap.forEach((occurances, label) => {
        if (occurances === 1) {
          diffDescriptions.push(`One ${label} ${changeKeyword}`);
        } else {
          diffDescriptions.push(
              `${occurances} ${label} entries ${changeKeyword}`);
        }
        numChanges += occurances;
      });
    };

    addToChanges(added, 'added');
    addToChanges(deleted, 'deleted');
    addToChanges(updated, 'updated');

    return [numChanges, diffDescriptions];
  }

  static getSnapshotChanges(current: Client, old?: Client): string[] {
    if (old === undefined) {
      return ['Client created'];
    }

    const diffDescriptions =
        ClientDetails.getDiffDescriptions(diff(old, current));

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
  getClientVersions(clientSnapshots: Client[]): ClientVersion[] {
    let clientChanges: ClientVersion[] = [];

    for (let i = 0; i < clientSnapshots.length; i++) {
      const clientChange = ClientDetails.getSnapshotChanges(
          clientSnapshots[i], clientSnapshots[i + 1]);
      if (clientChange.length !== 0) {
        clientChanges.push({
          client: clientSnapshots[i],
          changes: clientChange,
        });
      }
    }

    return clientChanges;
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
