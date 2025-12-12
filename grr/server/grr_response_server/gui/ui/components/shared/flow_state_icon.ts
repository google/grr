import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatBadgeModule} from '@angular/material/badge';
import {MatIconModule} from '@angular/material/icon';
import {MatTooltipModule} from '@angular/material/tooltip';

import {Flow, FlowState} from '../../lib/models/flow';
import {checkExhaustive} from '../../lib/utils';

/**
 * Component displaying the state of a Flow in a material icon.
 */
@Component({
  selector: 'flow-state-icon',
  templateUrl: './flow_state_icon.ng.html',
  styleUrls: ['./flow_state_icon.scss'],
  imports: [CommonModule, MatBadgeModule, MatIconModule, MatTooltipModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowStateIcon {
  readonly flow = input.required<Flow>();

  protected readonly checkExhaustive = checkExhaustive;
  protected readonly FlowState = FlowState;

  protected getFlowResultsCount(flow: Flow): number | undefined {
    // TODO: Filter count by flow type.
    return flow.resultCounts?.reduce(
      (sum, resultCount) => sum + (resultCount.count ?? 0),
      0,
    );
  }
}
