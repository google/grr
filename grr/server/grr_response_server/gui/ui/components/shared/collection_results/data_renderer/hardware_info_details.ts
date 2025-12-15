import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

import {HardwareInfo as HardwareInfoModel} from '../../../../lib/api/api_interfaces';

/**
 * Component displaying the hardware info.
 */
@Component({
  selector: 'hardware-info-details',
  templateUrl: './hardware_info_details.ng.html',
  styleUrls: ['./snapshot_tables.scss'],
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HardwareInfoDetails {
  readonly hardwareInfo = input.required<HardwareInfoModel | undefined>();
}
