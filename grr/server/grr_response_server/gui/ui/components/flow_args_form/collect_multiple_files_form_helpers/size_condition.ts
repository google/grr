import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormGroup} from '@angular/forms';

/** Form that configures a size condition. */
@Component({
  selector: 'size-condition',
  templateUrl: './size_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SizeCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  static createFormGroup(): FormGroup {
    return new FormGroup({});
  }
}
