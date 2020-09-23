import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {NetworkInterface} from '../../../lib/models/client';

/**
 * Component the details for a single NetworkInterface.
 */
@Component({
  selector: 'interfaces-details',
  templateUrl: './interfaces_details.ng.html',
  styleUrls: ['./interfaces_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InterfacesDetails {
  @Input() interfaces!: NetworkInterface[];
}
