import {Directive, ElementRef, forwardRef, Renderer2} from '@angular/core';
import {ControlValueAccessor, NG_VALUE_ACCESSOR} from '@angular/forms';

import {
  parseDurationString,
  toDurationString,
} from '../../../../lib/duration_conversion';

/** Angular provider to inject DurationValueAccessor. */
export const DURATION_VALUE_ACCESSOR = {
  provide: NG_VALUE_ACCESSOR,
  useExisting: forwardRef(() => DurationValueAccessor),
  multi: true,
};

type OnChangeFn = (value?: number) => void;
type OnTouchedFn = () => void;

/** DurantionTimeAccessor for handling duration input fields. */
@Directive({
  selector: '[durationInput]',
  host: {
    '(change)': 'onChange($event.target.value)',
    '(input)': 'onChange($event.target.value)',
    '(blur)': 'onTouched()',
  },
  providers: [DURATION_VALUE_ACCESSOR],
})
export class DurationValueAccessor implements ControlValueAccessor {
  private onChangeListener: OnChangeFn = () => {};
  onTouched: OnTouchedFn = () => {};

  constructor(
    private readonly renderer: Renderer2,
    private readonly el: ElementRef<HTMLInputElement>,
  ) {}

  writeValue(value: unknown): void {
    let durationString = '';
    if (value !== null && value !== undefined) {
      const castedValue = Number(value);
      if (Number.isFinite(castedValue)) {
        durationString = toDurationString(castedValue);
      }
    }

    this.renderer.setProperty(this.el.nativeElement, 'value', durationString);
  }

  onChange(value: string) {
    this.onChangeListener(robustParseDurationString(value));
  }

  registerOnChange(fn: OnChangeFn): void {
    this.onChangeListener = fn;
  }

  registerOnTouched(fn: OnTouchedFn): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.renderer.setProperty(this.el.nativeElement, 'disabled', isDisabled);
  }
}

function robustParseDurationString(value: string | null | undefined) {
  if (value === undefined || value === null) {
    return undefined;
  }

  try {
    return parseDurationString(value.toString());
  } catch (e: unknown) {
    return undefined;
  }
}
