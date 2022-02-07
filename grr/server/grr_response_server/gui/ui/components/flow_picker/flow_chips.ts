import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {BehaviorSubject} from 'rxjs';

import {FlowListItem} from '../../components/flow_picker/flow_list_item';

/**
 * Component that displays available Flows.
 */
@Component({
  selector: 'flow-chips',
  templateUrl: './flow_chips.ng.html',
  styleUrls: ['./flow_chips.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FlowChips {
  @Input()
  set flows(value: ReadonlyArray<FlowListItem>|null) {
    this.flows$.next(value ?? []);
  }

  get flows(): ReadonlyArray<FlowListItem> {
    return this.flows$.value;
  }

  readonly flows$ = new BehaviorSubject<ReadonlyArray<FlowListItem>>([]);

  /**
   * Event that is triggered when a flow is selected.
   */
  @Output() flowSelected = new EventEmitter<FlowListItem>();

  trackByFlowName(index: number, fli: FlowListItem): string {
    return fli.name;
  }
}
