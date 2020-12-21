import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';

/** Form that configures a CollectSingleFile flow. */
@Component({
  selector: 'condition-panel',
  templateUrl: './condition_panel.ng.html',
  styleUrls: ['./condition_panel.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConditionPanel {
  @Input() title!: string;
  @Output() conditionRemoved = new EventEmitter<void>();
}
