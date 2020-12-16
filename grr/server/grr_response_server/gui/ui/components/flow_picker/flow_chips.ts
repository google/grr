import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {FlowListItem} from '@app/components/flow_picker/flow_list_item';
import {BehaviorSubject} from 'rxjs';

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
  private flowsInternal: ReadonlyArray<FlowListItem> = [];

  @Input()
  set flows(value: ReadonlyArray<FlowListItem>) {
    this.flowsInternal = value;
    this.flows$.next(value);
  }

  get flows(): ReadonlyArray<FlowListItem> {
    return this.flowsInternal;
  }

  flows$ = new BehaviorSubject<ReadonlyArray<FlowListItem>>(this.flowsInternal);

  /**
   * Event that is triggered when a flow is selected.
   */
  @Output() flowSelected = new EventEmitter<FlowListItem>();

  trackByFlowName(fli: FlowListItem): string {
    return fli.name;
  }
}
