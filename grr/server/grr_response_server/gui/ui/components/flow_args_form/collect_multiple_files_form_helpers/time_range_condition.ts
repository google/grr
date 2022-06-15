import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup} from '@angular/forms';

import {atLeastOneMustBeSet, timesInOrder} from '../../../components/form/validators';
import {FileFinderAccessTimeCondition, FileFinderInodeChangeTimeCondition, FileFinderModificationTimeCondition} from '../../../lib/api/api_interfaces';
import {createOptionalApiTimestamp} from '../../../lib/api_translation/primitive';
import {DateTime} from '../../../lib/date_time';

/** Form that configures a modification time condition. */
@Component({
  selector: 'time-range-condition',
  templateUrl: './time_range_condition.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TimeRangeCondition {
  constructor(readonly controlContainer: ControlContainer) {}

  @Input() title: string = '';
  @Output() conditionRemoved = new EventEmitter<void>();

  get formGroup() {
    return this.controlContainer.control as
        ReturnType<typeof createTimeRangeFormGroup>;
  }
}

/** Initializes a form group corresponding to the time range condition. */
export function createTimeRangeFormGroup() {
  const minTime = new FormControl<DateTime|null|undefined>(null);
  const maxTime = new FormControl<DateTime|null|undefined>(null);

  return new FormGroup({'minTime': minTime, 'maxTime': maxTime}, {
    validators: [
      atLeastOneMustBeSet([minTime, maxTime]),
      timesInOrder(minTime, maxTime),
    ]
  });
}

type RawFormValues = ReturnType<typeof createTimeRangeFormGroup>['value'];

/** Converts raw form values to FileFinderModificationTimeCondition. */
export function formValuesToFileFinderModificationTimeCondition(
    rawFormValues: RawFormValues): FileFinderModificationTimeCondition {
  return {
    minLastModifiedTime: createOptionalApiTimestamp(rawFormValues.minTime),
    maxLastModifiedTime: createOptionalApiTimestamp(rawFormValues.maxTime),
  };
}

/** Converts raw form values to FileFinderAccessTimeCondition. */
export function formValuesToFileFinderAccessTimeCondition(
    rawFormValues: RawFormValues): FileFinderAccessTimeCondition {
  return {
    minLastAccessTime: createOptionalApiTimestamp(rawFormValues.minTime),
    maxLastAccessTime: createOptionalApiTimestamp(rawFormValues.maxTime),
  };
}

/** Converts raw form values to FileFinderInodeChangeTimeCondition. */
export function formValuesToFileFinderInodeChangeTimeCondition(
    rawFormValues: RawFormValues): FileFinderInodeChangeTimeCondition {
  return {
    minLastInodeChangeTime: createOptionalApiTimestamp(rawFormValues.minTime),
    maxLastInodeChangeTime: createOptionalApiTimestamp(rawFormValues.maxTime),
  };
}
