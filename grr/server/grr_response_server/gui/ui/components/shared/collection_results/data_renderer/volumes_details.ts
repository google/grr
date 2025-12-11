import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {StorageVolume} from '../../../../lib/models/client';
import {HumanReadableByteSizePipe} from '../../../../pipes/human_readable/human_readable_byte_size_pipe';
import {CopyButton} from '../../copy_button';
import {Timestamp} from '../../timestamp';

/**
 * Component the details for a list of StorageVolumes.
 */
@Component({
  selector: 'volumes-details',
  templateUrl: './volumes_details.ng.html',
  styleUrls: ['./snapshot_tables.scss'],
  imports: [CommonModule, CopyButton, HumanReadableByteSizePipe, Timestamp],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VolumesDetails {
  readonly volumes = input.required<readonly StorageVolume[]>();

  protected readonly String = String;
}
