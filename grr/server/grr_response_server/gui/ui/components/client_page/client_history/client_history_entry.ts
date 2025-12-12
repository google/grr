import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  Input as RouterInput,
  signal,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatDialog} from '@angular/material/dialog';
import {MatIconModule} from '@angular/material/icon';
import {RouterModule} from '@angular/router';

import {
  archAccessor,
  ClientSnapshot as ClientSnapshotModel,
  cloudInstanceAccessor,
  hardwareInfoAccessor,
  knowledgeBaseAccessor,
  memorySizeAccessor,
  networkInterfacesAccessor,
  osInstallDateAccessor,
  osKernelAccessor,
  osReleaseAccessor,
  osVersionAccessor,
  startupInfoAccessor,
  usersAccessor,
  volumesAccessor,
} from '../../../lib/models/client';
import {HumanReadableByteSizePipe} from '../../../pipes/human_readable/human_readable_byte_size_pipe';
import {ClientStore} from '../../../store/client_store';
import {CloudInstanceDetails} from '../../shared/collection_results/data_renderer/cloud_instance_details';
import {HardwareInfoDetails} from '../../shared/collection_results/data_renderer/hardware_info_details';
import {KnowledgeBaseDetails} from '../../shared/collection_results/data_renderer/knowledge_base_details';
import {NetworkInterfacesDetails} from '../../shared/collection_results/data_renderer/network_interfaces_details';
import {StartupInfoDetails} from '../../shared/collection_results/data_renderer/startup_info_details';
import {UsersDetails} from '../../shared/collection_results/data_renderer/users_details';
import {VolumesDetails} from '../../shared/collection_results/data_renderer/volumes_details';
import {CopyButton} from '../../shared/copy_button';
import {Timestamp} from '../../shared/timestamp';
import {
  SnapshotEntryHistoryDialog,
  SnapshotEntryHistoryDialogData,
} from './snapshot_entry_history_dialog';

const INITIAL_NUM_USERS_SHOWN = 1;
const INITIAL_NUM_INTERFACES_SHOWN = 3;
const INITIAL_NUM_VOLUMES_SHOWN = 2;

/**
 * Component displaying a Client snapshot.
 */
@Component({
  selector: 'client-history-entry',
  templateUrl: './client_history_entry.ng.html',
  styleUrls: ['./client_history_entry.scss'],
  imports: [
    CloudInstanceDetails,
    CommonModule,
    CopyButton,
    HardwareInfoDetails,
    HumanReadableByteSizePipe,
    KnowledgeBaseDetails,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    NetworkInterfacesDetails,
    RouterModule,
    StartupInfoDetails,
    Timestamp,
    UsersDetails,
    VolumesDetails,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientHistoryEntry {
  private readonly dialog = inject(MatDialog);

  readonly clientStore = inject(ClientStore);

  private readonly selectedTimestamp = signal<number>(0);

  @RouterInput()
  set historyTimestamp(timestamp: string) {
    this.selectedTimestamp.set(Number(timestamp));
  }

  // Depending on how the snapshot is accessed - via selecting an entry from the
  // client history or via the URL - the router input or the store with the
  // client snapshots might be updated first. By storing the timestamp from the
  // router input in a signal and using a computed signal, both cases are
  // handled correctly.
  protected readonly clientSnapshot = computed(() => {
    return this.clientStore.clientSnapshots().find((snapshot) => {
      const snapshotTimestamp = snapshot.timestamp?.getTime() ?? 0;
      return snapshotTimestamp === this.selectedTimestamp();
    });
  });

  protected readonly startupInfo = computed(() => {
    return this.clientStore.clientStartupInfos().find((startupInfo) => {
      const startupInfoTimestamp = startupInfo.timestamp?.getTime() ?? 0;
      return startupInfoTimestamp === this.selectedTimestamp();
    });
  });

  // Depdening on the machine there might be a lot of users, interfaces and
  // volumes. We only show a few by default and provide a button to show more.
  protected INITIAL_NUM_USERS_SHOWN = INITIAL_NUM_USERS_SHOWN;
  protected INITIAL_NUM_INTERFACES_SHOWN = INITIAL_NUM_INTERFACES_SHOWN;
  protected INITIAL_NUM_VOLUMES_SHOWN = INITIAL_NUM_VOLUMES_SHOWN;

  protected currentNumUsersShown = INITIAL_NUM_USERS_SHOWN;
  protected currentNumInterfacesShown = INITIAL_NUM_INTERFACES_SHOWN;
  protected currentNumVolumesShown = INITIAL_NUM_VOLUMES_SHOWN;

  openSnapshotEntryHistoryDialog(
    accessor: (snapshot: ClientSnapshotModel) => string,
  ) {
    const dialogData: SnapshotEntryHistoryDialogData = {
      snapshots: this.clientStore.clientSnapshots(),
      entryAccessor: accessor,
    };
    this.dialog.open(SnapshotEntryHistoryDialog, {data: dialogData});
  }

  protected readonly archAccessor = archAccessor;
  protected readonly cloudInstanceAccessor = cloudInstanceAccessor;
  protected readonly hardwareInfoAccessor = hardwareInfoAccessor;
  protected readonly knowledgeBaseAccessor = knowledgeBaseAccessor;
  protected readonly memorySizeAccessor = memorySizeAccessor;
  protected readonly networkInterfacesAccessor = networkInterfacesAccessor;
  protected readonly osInstallDateAccessor = osInstallDateAccessor;
  protected readonly osKernelAccessor = osKernelAccessor;
  protected readonly osReleaseAccessor = osReleaseAccessor;
  protected readonly osVersionAccessor = osVersionAccessor;
  protected readonly usersAccessor = usersAccessor;
  protected readonly volumesAccessor = volumesAccessor;
  protected readonly startupInfoAccessor = startupInfoAccessor;
}
