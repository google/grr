import {Component, Input, ViewEncapsulation} from '@angular/core';

/**
 * Shows a formatted timestamp, based on the date received as parameter 
 */
@Component({
  selector: 'timestamp',
  templateUrl: './timestamp.ng.html',
  styleUrls: ['./timestamp.scss'],
  encapsulation: ViewEncapsulation.None
})
export class Timestamp {
  @Input() date?: Date;
}
