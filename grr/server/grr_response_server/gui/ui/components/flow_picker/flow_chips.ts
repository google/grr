import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import {BehaviorSubject} from 'rxjs';

import {FlowListItem} from '../../lib/models/flow';

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
  set flows(value: readonly FlowListItem[] | null) {
    this.flows$.next(value ?? []);
  }

  get flows(): readonly FlowListItem[] {
    return this.flows$.value;
  }

  readonly flows$ = new BehaviorSubject<readonly FlowListItem[]>([]);

  /**
   * Event that is triggered when a flow is selected.
   */
  @Output() readonly flowSelected = new EventEmitter<FlowListItem>();

  trackByFlowType(index: number, fli: FlowListItem): string {
    return fli.type;
  }
}
