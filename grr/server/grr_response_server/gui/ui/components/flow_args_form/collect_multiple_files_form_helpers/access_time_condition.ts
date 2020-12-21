import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormGroup} from '@angular/forms';

/** Form that configures an access time condition. */
@Component({
  selector: 'access-time-condition',
  templateUrl: './access_time_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccessTimeCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  static createFormGroup(): FormGroup {
    return new FormGroup({});
  }
}
