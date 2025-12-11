import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';

import {
  CloudInstance,
  CloudInstanceInstanceType,
} from '../../../../lib/api/api_interfaces';
import {CopyButton} from '../../copy_button';

/**
 * Component displaying the hardware info.
 */
@Component({
  selector: 'cloud-instance-details',
  templateUrl: './cloud_instance_details.ng.html',
  styleUrls: ['./snapshot_tables.scss'],
  imports: [CommonModule, CopyButton, MatChipsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CloudInstanceDetails {
  readonly cloudInstance = input.required<CloudInstance | undefined>();

  protected readonly CloudInstanceInstanceType = CloudInstanceInstanceType;
}
