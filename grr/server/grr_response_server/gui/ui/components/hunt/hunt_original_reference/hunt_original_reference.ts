import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {RouterModule} from '@angular/router';

import {
  type ApiFlowReference,
  type ApiHuntReference,
} from '../../../lib/api/api_interfaces';
import {CopyButtonModule} from '../../helpers/copy_button/copy_button_module';

/** Displays original hunt or flow reference. */
@Component({
  selector: 'hunt-original-reference',
  templateUrl: './hunt_original_reference.ng.html',
  styleUrls: ['./hunt_original_reference.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true,
  imports: [CommonModule, CopyButtonModule, RouterModule],
})
export class HuntOriginalReference {
  @Input() huntRef: ApiHuntReference | undefined = undefined;
  @Input() flowRef: ApiFlowReference | undefined = undefined;
}
