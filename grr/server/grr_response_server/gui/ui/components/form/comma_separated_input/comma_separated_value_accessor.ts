import {Directive, ElementRef, forwardRef, Renderer2} from '@angular/core';
import {ControlValueAccessor, NG_VALUE_ACCESSOR} from '@angular/forms';

/** Angular provider to inject CommaSeparatedValueAccessor. */
export const COMMA_SEPARATED_VALUE_ACCESSOR = {
  provide: NG_VALUE_ACCESSOR,
  useExisting: forwardRef(() => CommaSeparatedValueAccessor),
  multi: true
};

type OnChangeFn = (value: ReadonlyArray<string>) => void;
type OnTouchedFn = () => void;

/** ControlValueAccessor for handling comma-separated values. */
@Directive({
  selector: '[commaSeparatedInput]',
  host: {
    '(change)': 'onChange($event.target.value)',
    '(input)': 'onChange($event.target.value)',
    '(blur)': 'onTouched()',
  },
  providers: [COMMA_SEPARATED_VALUE_ACCESSOR]
})
export class CommaSeparatedValueAccessor implements ControlValueAccessor {
  private onChangeListener: OnChangeFn = () => {};
  onTouched: OnTouchedFn = () => {};

  constructor(
      private readonly renderer: Renderer2,
      private readonly el: ElementRef<HTMLInputElement>) {}

  writeValue(value: Iterable<string>|null|undefined): void {
    this.renderer.setProperty(
        this.el.nativeElement, 'value', Array.from(value ?? []).join(', '));
  }

  onChange(value: string) {
    this.onChangeListener(parseCommaSeparatedString(value));
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

function parseCommaSeparatedString(value: string|null|undefined) {
  return (value ?? '').split(',').map(item => item.trim()).filter(item => item);
}
