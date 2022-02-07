import {FocusMonitor} from '@angular/cdk/a11y';
import {coerceBooleanProperty} from '@angular/cdk/coercion';
import {ChangeDetectionStrategy, ChangeDetectorRef, Component, ElementRef, forwardRef, HostBinding, Input, OnDestroy, Optional, Self, ViewChild} from '@angular/core';
import {ControlValueAccessor, NgControl} from '@angular/forms';
import {MatFormFieldControl} from '@angular/material/form-field';
import {MatMenu, MatMenuTrigger} from '@angular/material/menu';
import {Subject} from 'rxjs';

import {DateTime} from '../../../lib/date_time';
import {isNonNull} from '../../../lib/preconditions';



const DATE_TIME_MAT_FORM_FIELD = {
  provide: MatFormFieldControl,
  useExisting: forwardRef(() => DateTimeInput)
};

type OnChangeFn = (value?: DateTime) => void;
type OnTouchedFn = () => void;


function generateMenuTimes(): ReadonlyArray<string> {
  const result: string[] = [];
  for (let hour = 0; hour < 24; ++hour) {
    for (let minute = 0; minute < 60; minute += 15) {
      const hourStr = hour.toString().padStart(2, '0');
      const minuteStr = minute.toString().padStart(2, '0');

      result.push(`${hourStr}:${minuteStr}`);
    }
  }

  return result;
}

/** DateTime format used in date-time-input controls. */
export const DATE_TIME_FORMAT = 'yyyy-MM-dd HH:mm:ss';

/** mat-form-field for GlobExpression inputs. */
@Component({
  selector: 'date-time-input',
  templateUrl: './date_time_input.ng.html',
  styleUrls: ['./date_time_input.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    DATE_TIME_MAT_FORM_FIELD,
  ],
})
export class DateTimeInput implements ControlValueAccessor,
                                      MatFormFieldControl<DateTime>, OnDestroy {
  private onChange: OnChangeFn = () => {};
  private inputStringInternal = '';
  onTouched: OnTouchedFn = () => {};

  @Input()
  dateTimeValueInternal = DateTime.utc().set({
    hour: 0,
    minute: 0,
    second: 0,
    millisecond: 0,
  });
  @ViewChild('calendarMenu') calendarMenu!: MatMenu;
  @ViewChild('clockMenu') clockMenu!: MatMenu;
  @ViewChild('calendarMenuTrigger') calendarMenuTrrigger!: MatMenuTrigger;
  @ViewChild('clockMenuTrigger') clockMenuTrigger!: MatMenuTrigger;

  menuTimes = generateMenuTimes();

  constructor(
      @Optional() @Self() public ngControl: NgControl,
      private readonly focusMonitor: FocusMonitor,
      private readonly el: ElementRef<HTMLElement>,
      private readonly changeDetectorRef: ChangeDetectorRef) {
    if (isNonNull(this.ngControl)) {
      this.ngControl.valueAccessor = this;
    }

    this.focusMonitor.monitor(this.el.nativeElement, true).subscribe(origin => {
      this.focused = !!origin;
      this.stateChanges.next();
    });
  }

  setClock(s: string) {
    const d = this.dateTimeValueInternal.invalidReason ?
        DateTime.utc() :
        this.dateTimeValueInternal;

    const [hour, minute] = s.split(':').map(Number);
    this.writeValue(d.set({
      hour,
      minute,
      second: 0,
      millisecond: 0,
    }));
  }

  setDate(date: Date) {
    this.calendarMenuTrrigger.closeMenu();

    const d = this.dateTimeValueInternal.invalidReason ?
        DateTime.utc().set({
          hour: 0,
          minute: 0,
          millisecond: 0,
        }) :
        this.dateTimeValueInternal;
    this.writeValue(d.set({
      year: date.getFullYear(),
      month: date.getMonth() + 1,
      day: date.getDate(),
    }));
  }

  get inputString(): string {
    return this.inputStringInternal;
  }

  set inputString(value: string) {
    if (value === this.inputStringInternal) {
      return;
    }
    this.inputStringInternal = value;
    this.changeDetectorRef.markForCheck();

    if (!this.ngControl.control) {
      return;
    }

    if (this.inputStringInternal === '') {
      this.writeValue(undefined);
      const errors = this.ngControl.control.errors ?? {};
      delete errors['invalidDateTime'];
      this.ngControl.control.setErrors(
          Object.keys(errors).length > 0 ? errors : null);
    } else {
      const dt = DateTime.fromFormat(value, DATE_TIME_FORMAT, {zone: 'utc'});
      this.writeValue(dt);

      if (dt.invalidReason) {
        const explanation = dt.invalidExplanation ?? '';
        this.ngControl.control.setErrors({
          'invalidDateTime': explanation !== '' ?
              explanation[0].toUpperCase() + explanation.slice(1) :
              ''
        });
      } else {
        const errors = this.ngControl.control.errors ?? {};
        delete errors['invalidDateTime'];
        this.ngControl.control.setErrors(
            Object.keys(errors).length > 0 ? errors : null);
      }
    }
  }

  // ControlValueAccessor implementation.
  writeValue(value?: DateTime): void {
    if (value) {
      this.dateTimeValueInternal = value;
      if (!value.invalidReason) {
        this.inputString = value.toUTC().toFormat(DATE_TIME_FORMAT);
      }
    } else {
      this.inputString = '';
    }
    this.onChange(value);
    this.onTouched();
    this.stateChanges.next();
  }

  registerOnChange(fn: OnChangeFn): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: OnTouchedFn): void {
    this.onTouched = fn;
  }

  // MatFormFieldControl implementation.
  stateChanges = new Subject<void>();
  private placeholderInternal = 'Input date/time';
  focused = false;
  controlType = 'date-time-input';
  private requiredInternal = false;
  private disabledInternal = false;

  static nextId = 0;
  @HostBinding() id = `date-time-input-${DateTimeInput.nextId++}`;

  get errorState(): boolean {
    return !!this.ngControl && !!this.ngControl.invalid;
  }

  @Input()
  get value(): DateTime {
    return this.dateTimeValueInternal;
  }
  set value(value: DateTime) {
    this.writeValue(value);
  }

  @Input()
  get placeholder() {
    return this.placeholderInternal;
  }
  set placeholder(placeholder: string) {
    this.placeholderInternal = placeholder;
    this.stateChanges.next();
  }

  @Input()
  get required(): boolean {
    return this.requiredInternal;
  }
  set required(required: boolean) {
    this.requiredInternal = coerceBooleanProperty(required);
    this.stateChanges.next();
  }

  @Input()
  get disabled(): boolean {
    return this.disabledInternal;
  }
  set disabled(disabled: boolean) {
    this.disabledInternal = coerceBooleanProperty(disabled);
    this.stateChanges.next();
  }

  get empty() {
    return this.inputString === '';
  }

  @HostBinding('attr.aria-describedby') describedBy = '';
  setDescribedByIds(ids: string[]) {
    this.describedBy = ids.join(' ');
  }

  @HostBinding('class.floating')
  get shouldLabelFloat() {
    return this.focused || !this.empty;
  }

  onContainerClick(event: MouseEvent) {
    this.focused = true;
    this.onTouched();
  }

  // OnDestroy implementation.
  ngOnDestroy() {
    this.stateChanges.complete();
    this.focusMonitor.stopMonitoring(this.el.nativeElement);
  }

  // Callbacks to be used by DateTimeInputToggle.
  calendarClick() {
    this.calendarMenuTrrigger.openMenu();
  }

  clockClick() {
    this.clockMenuTrigger.openMenu();
  }
}
