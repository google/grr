import {Directive, ElementRef, forwardRef, Renderer2} from '@angular/core';
import {ControlValueAccessor, NG_VALUE_ACCESSOR} from '@angular/forms';

import {parseByteString, toByteString} from './byte_conversion';

/** Angular provider to inject ByteValueAccessor. */
export const BYTE_VALUE_ACCESSOR = {
  provide: NG_VALUE_ACCESSOR,
  useExisting: forwardRef(() => ByteValueAccessor),
  multi: true,
};

type OnChangeFn = (value?: number) => void;
type OnTouchedFn = () => void;

/** ControlValueAccessor for handling byte input fields. */
@Directive({
  selector: '[byteInput]',
  host: {
    '(change)': 'onChange($event.target.value)',
    '(input)': 'onChange($event.target.value)',
    '(blur)': 'onTouched()',
  },
  providers: [BYTE_VALUE_ACCESSOR],
})
export class ByteValueAccessor implements ControlValueAccessor {
  private onChangeListener: OnChangeFn = () => {};
  onTouched: OnTouchedFn = () => {};

  constructor(
    private readonly renderer: Renderer2,
    private readonly el: ElementRef<HTMLInputElement>,
  ) {}

  writeValue(value: unknown): void {
    let byteString = '';

    if (value !== null && value !== undefined) {
      const castedValue = Number(value);
      if (Number.isFinite(castedValue)) {
        byteString = toByteString(castedValue);
      }
    }

    this.renderer.setProperty(this.el.nativeElement, 'value', byteString);
  }

  onChange(value: string) {
    this.onChangeListener(robustParseByteString(value));
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

function robustParseByteString(value: string | null | undefined) {
  if (value === undefined || value === null) {
    return undefined;
  }

  try {
    return parseByteString(value.toString());
  } catch (e) {
    return undefined;
  }
}
