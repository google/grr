import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {NetworkInterface} from '../../../../lib/models/client';
import {CopyButton} from '../../copy_button';

/**
 * Component the details for a list of NetworkInterfaces.
 */
@Component({
  selector: 'network-interfaces-details',
  templateUrl: './network_interfaces_details.ng.html',
  styleUrls: ['./snapshot_tables.scss'],
  imports: [CommonModule, CopyButton],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NetworkInterfacesDetails {
  readonly interfaces = input.required<readonly NetworkInterface[]>();
}
