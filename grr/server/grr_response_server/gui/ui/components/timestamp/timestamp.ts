import {Component, Input} from '@angular/core';

/**
 * Shows a formatted timestamp, based on the date received as parameter.
 */
@Component({
  selector: 'timestamp',
  templateUrl: './timestamp.ng.html',
  styleUrls: ['./timestamp.scss'],
})
export class Timestamp {
  @Input() date?: Date;
  @Input() absoluteOnly: boolean = false;
  @Input() tooltipEnabled: boolean = true;
}
