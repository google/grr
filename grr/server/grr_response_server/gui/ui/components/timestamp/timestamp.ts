import {Component, Input, ViewEncapsulation} from '@angular/core';

/**
 * Shows a formatted timestamp, based on the date received as parameter.
 */
@Component({
  selector: 'timestamp',
  templateUrl: './timestamp.ng.html',
  styleUrls: ['./timestamp.scss'],
  // Disabled style encapsulation is needed because of matTooltip.
  // matTooltip uses an overlay which is placed at a separate
  // place in the DOM. Thus, the only way to apply custom styles
  // to the matTooltip is by effectively making the styles global.
  encapsulation: ViewEncapsulation.None,
})
export class Timestamp {
  @Input() date?: Date;
  @Input() completeFormat: boolean = false;
  @Input() tooltipEnabled: boolean = true;
  @Input() forceDisableUnderlining: boolean = false;
  readonly timezone: string = 'UTC';
}
