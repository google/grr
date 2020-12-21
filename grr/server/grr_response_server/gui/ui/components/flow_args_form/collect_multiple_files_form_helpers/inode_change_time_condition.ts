import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormGroup} from '@angular/forms';

/** Form that configures an ext flags condition. */
@Component({
  selector: 'inode-change-time-condition',
  templateUrl: './inode_change_time_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InodeChangeTimeCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  static createFormGroup(): FormGroup {
    return new FormGroup({});
  }
}
