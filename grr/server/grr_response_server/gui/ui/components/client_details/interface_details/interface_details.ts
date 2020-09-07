import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {NetworkInterface} from '@app/lib/models/client';

/**
 * Component the details for a single NetworkInterface.
 */
@Component({
  selector: 'interface-details',
  templateUrl: './interface_details.ng.html',
  styleUrls: ['./interface_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InterfaceDetails {
  @Input() interface!: NetworkInterface;
}
