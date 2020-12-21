import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormGroup} from '@angular/forms';

/** Form that configures an ext flags condition. */
@Component({
  selector: 'ext-flags-condition',
  templateUrl: './ext_flags_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExtFlagsCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  static createFormGroup(): FormGroup {
    return new FormGroup({});
  }
}
