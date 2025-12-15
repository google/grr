import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';

import {ClientSnapshot as ApiClientSnapshot} from '../../../lib/api/api_interfaces';
import {translateClientSnapshot} from '../../../lib/api/translation/client';
import {ClientSnapshot} from '../../../lib/models/client';
import {isHuntResult} from '../../../lib/models/hunt';
import {CollectionResult} from '../../../lib/models/result';
import {CopyButton} from '../copy_button';
import {Timestamp} from '../timestamp';
import {CloudInstanceDetails} from './data_renderer/cloud_instance_details';
import {HardwareInfoDetails} from './data_renderer/hardware_info_details';
import {KnowledgeBaseDetails} from './data_renderer/knowledge_base_details';
import {NetworkInterfacesDetails} from './data_renderer/network_interfaces_details';
import {StartupInfoDetails} from './data_renderer/startup_info_details';
import {UsersDetails} from './data_renderer/users_details';
import {VolumesDetails} from './data_renderer/volumes_details';

/** Component that displays `ClientSnapshot` collection results. */
@Component({
  selector: 'client-snapshots',
  templateUrl: './client_snapshots.ng.html',
  styleUrls: ['./collection_result_styles.scss', './client_snapshots.scss'],
  imports: [
    CloudInstanceDetails,
    CommonModule,
    CopyButton,
    HardwareInfoDetails,
    KnowledgeBaseDetails,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    NetworkInterfacesDetails,
    StartupInfoDetails,
    Timestamp,
    UsersDetails,
    VolumesDetails,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientSnapshots {
  collectionResults = input.required<readonly CollectionResult[]>();

  protected isHuntResult = isHuntResult;

  protected clientSnapshotsFromCollectionResult(
    collectionResult: CollectionResult,
  ): ClientSnapshot {
    return translateClientSnapshot(
      collectionResult.payload as ApiClientSnapshot,
    );
  }
}
