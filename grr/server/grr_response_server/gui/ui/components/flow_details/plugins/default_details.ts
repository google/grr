import {ChangeDetectionStrategy, Component} from '@angular/core';

import {Plugin} from './plugin';

/** Fallback component when flow results have not been implemented. */
@Component({
  selector: 'default-flow-details',
  templateUrl: './default_details.ng.html',
  styleUrls: ['./default_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DefaultDetails extends Plugin {
}
