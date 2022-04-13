import {ChangeDetectionStrategy, Component} from '@angular/core';

import {FlowState} from '../../../lib/models/flow';

import {Plugin} from './plugin';

/** Results view for Interrogate flow. */
@Component({
  selector: 'app-interrogate-details',
  templateUrl: './interrogate_details.ng.html',
  styleUrls: ['./interrogate_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InterrogateDetails extends Plugin {
  readonly flowState = FlowState;
}
