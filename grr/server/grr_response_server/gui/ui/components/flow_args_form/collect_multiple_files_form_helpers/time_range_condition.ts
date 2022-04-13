import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';
import {ControlContainer, UntypedFormControl, UntypedFormGroup} from '@angular/forms';

import {atLeastOneMustBeSet, timesInOrder} from '../../../components/form/validators';
import {FileFinderAccessTimeCondition, FileFinderInodeChangeTimeCondition, FileFinderModificationTimeCondition} from '../../../lib/api/api_interfaces';
import {createOptionalApiTimestamp} from '../../../lib/api_translation/primitive';
import {DateTime} from '../../../lib/date_time';


/** Represents raw values produced by the time range form. */
export declare interface RawFormValues {
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

  get formGroup(): UntypedFormGroup {
    return this.controlContainer.control as UntypedFormGroup;
  }
}

/** Initializes a form group corresponding to the time range condition. */
export function createTimeRangeFormGroup(): UntypedFormGroup {
  const minTime = new UntypedFormControl(null);
  const maxTime = new UntypedFormControl(null);

  return new UntypedFormGroup({'minTime': minTime, 'maxTime': maxTime}, [
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
    maxLastInodeChangeTime: createOptionalApiTimestamp(rawFormValues.maxTime),
  };
}
