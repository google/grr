import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup} from '@angular/forms';
import {atLeastOneMustBeSet, timesInOrder} from '@app/components/form/validators';
import {FileFinderAccessTimeCondition, FileFinderInodeChangeTimeCondition, FileFinderModificationTimeCondition} from '@app/lib/api/api_interfaces';
import {createOptionalApiTimestamp} from '@app/lib/api_translation/primitive';
import {DateTime} from '@app/lib/date_time';


/** Represents raw values produced by the time range form. */
export interface RawFormValues {
  readonly minTime: DateTime|null;
  readonly maxTime: DateTime|null;
}

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

  get formGroup(): FormGroup {
    return this.controlContainer.control as FormGroup;
  }
}

/** Initializes a form group corresponding to the time range condition. */
export function createTimeRangeFormGroup(): FormGroup {
  const minTime = new FormControl(null);
  const maxTime = new FormControl(null);

  return new FormGroup(
      {
        minTime,
        maxTime,
      },
      [
        atLeastOneMustBeSet([minTime, maxTime]),
        timesInOrder(minTime, maxTime),
      ]);
}

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
    maxLastInodeChangeTIme: createOptionalApiTimestamp(rawFormValues.maxTime),
  };
}
