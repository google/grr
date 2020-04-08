import {ChangeDetectionStrategy, Component} from '@angular/core';
import {Plugin} from './plugin';

/**
 * Component that allows selecting, configuring, and starting a Flow.
 */
@Component({
  selector: 'default-flow-details',
  templateUrl: './default_details.ng.html',
  styleUrls: ['./default_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DefaultDetails extends Plugin {
}
