import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {NetworkInterface} from '@app/lib/models/client';

/**
 * Component the details for a single NetworkInterface.
 */
@Component({
  selector: 'interfaces-details',
  templateUrl: './interfaces_details.ng.html',
  styleUrls: ['./interfaces_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InterfaceDetails {
  @Input() interfaces!: NetworkInterface[];
}
