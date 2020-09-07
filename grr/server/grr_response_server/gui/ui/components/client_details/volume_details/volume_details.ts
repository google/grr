import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {StorageVolume} from '@app/lib/models/client';

/**
 * Component the details for a single StorageVolume.
 */
@Component({
  selector: 'volume-details',
  templateUrl: './volume_details.ng.html',
  styleUrls: ['./volume_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VolumeDetails {
  @Input() volume!: StorageVolume;
}
