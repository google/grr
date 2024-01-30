import {ChangeDetectionStrategy, Component} from '@angular/core';

/**
 * Component displaying the details for a single hunt result.
 */
@Component({
  selector: 'hunt-help',
  templateUrl: './hunt_help.ng.html',
  styleUrls: ['./hunt_help.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntHelp {}
