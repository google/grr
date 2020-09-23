import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {StorageVolume} from '../../../lib/models/client';

/**
 * Component the details for a single StorageVolume.
 */
@Component({
  selector: 'volumes-details',
  templateUrl: './volumes_details.ng.html',
  styleUrls: ['./volumes_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VolumesDetails {
  @Input() volumes!: StorageVolume[];
}
