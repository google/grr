import {ChangeDetectionStrategy, Component, EventEmitter, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup} from '@angular/forms';

/** Form that configures a modification time condition. */
@Component({
  selector: 'modification-time-condition',
  templateUrl: './modification_time_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModificationTimeCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Output() conditionRemoved = new EventEmitter<void>();

  static createFormGroup(): FormGroup {
    return new FormGroup({
      minLastModifiedTime: new FormControl(0),
      maxLastModifiedTime: new FormControl(0),
    });
  }
}
