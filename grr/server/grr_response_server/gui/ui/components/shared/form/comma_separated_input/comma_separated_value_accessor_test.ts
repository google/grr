import {Component, DebugElement} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule, UntypedFormControl} from '@angular/forms';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CommaSeparatedNumberValueAccessor,
  CommaSeparatedValueAccessor,
} from './comma_separated_value_accessor';

@Component({
  template: '<input commaSeparatedInput [formControl]="formControl">',
  imports: [CommaSeparatedValueAccessor, ReactiveFormsModule],
})
class TestHostComponent {
  readonly formControl = new UntypedFormControl();
}

describe('Comma Separated Value Accessor', () => {
  describe('Comma Separated Input Accessor', () => {
    let fixture: ComponentFixture<TestHostComponent>;
    let input: DebugElement;

    beforeEach(waitForAsync(() => {
      TestBed.configureTestingModule({
        imports: [TestHostComponent, NoopAnimationsModule],
        teardown: {destroyAfterEach: false},
      }).compileComponents();

      fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      input = fixture.debugElement.query(By.css('input'));
    }));

    it('is applied on [commaSeparatedInput]', () => {
      const el = fixture.debugElement.query(
        By.directive(CommaSeparatedValueAccessor),
      );
      expect(el).toBeTruthy();
    });

    it('writes an empty list as empty string', () => {
      fixture.componentInstance.formControl.setValue([]);
      fixture.detectChanges();
      expect(input.nativeElement.value).toEqual('');
    });

    it('writes a single value without delimiter', () => {
      fixture.componentInstance.formControl.setValue(['abc']);
      fixture.detectChanges();
      expect(input.nativeElement.value).toEqual('abc');
    });

    it('comma-separates multiple values', () => {
      fixture.componentInstance.formControl.setValue(['Abc', 'dEf', 'HIJ']);
      fixture.detectChanges();
      expect(input.nativeElement.value).toEqual('Abc, dEf, HIJ');
    });

    it('parses an input without comma to a single value', () => {
      input.nativeElement.value = 'abc';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual(['abc']);
    });

    it('parses comma-separated inputs to an array', () => {
      input.nativeElement.value = 'Abc,dEf,HIJ';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual([
        'Abc',
        'dEf',
        'HIJ',
      ]);
    });

    it('ignores whitespace around entries', () => {
      input.nativeElement.value = '  Abc   , dEf  , HIJ  ';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual([
        'Abc',
        'dEf',
        'HIJ',
      ]);
    });

    it('ignores empty entries between delimiters', () => {
      input.nativeElement.value = ',  Abc   ,,, dEf , , HIJ , ';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual([
        'Abc',
        'dEf',
        'HIJ',
      ]);
    });
  });

  @Component({
    template: '<input commaSeparatedNumberInput [formControl]="formControl">',
    imports: [CommaSeparatedNumberValueAccessor, ReactiveFormsModule],
  })
  class TestHostNumberComponent {
    readonly formControl = new UntypedFormControl();
  }

  describe('Comma Separated Number Input Accessor', () => {
    let fixture: ComponentFixture<TestHostNumberComponent>;
    let input: DebugElement;

    beforeEach(waitForAsync(() => {
      TestBed.configureTestingModule({
        imports: [NoopAnimationsModule, TestHostNumberComponent],
        teardown: {destroyAfterEach: false},
      }).compileComponents();

      fixture = TestBed.createComponent(TestHostNumberComponent);
      fixture.detectChanges();

      input = fixture.debugElement.query(By.css('input'));
    }));

    it('is applied on [commaSeparatedNumberInput]', () => {
      const el = fixture.debugElement.query(
        By.directive(CommaSeparatedNumberValueAccessor),
      );
      expect(el).toBeTruthy();
    });

    it('writes an empty list as empty string', () => {
      fixture.componentInstance.formControl.setValue([]);
      fixture.detectChanges();
      expect(input.nativeElement.value).toEqual('');
    });

    it('writes a single value without delimiter', () => {
      fixture.componentInstance.formControl.setValue([123]);
      fixture.detectChanges();
      expect(input.nativeElement.value).toEqual('123');
    });

    it('comma-separates multiple values', () => {
      fixture.componentInstance.formControl.setValue([123, 456, 123]);
      fixture.detectChanges();
      expect(input.nativeElement.value).toEqual('123, 456, 123');
    });

    it('parses an input without comma to a single value', () => {
      input.nativeElement.value = '246';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual([246]);
    });

    it('parses comma-separated inputs to an array', () => {
      input.nativeElement.value = '12,34,56';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual([12, 34, 56]);
    });

    it('ignores whitespace around entries', () => {
      input.nativeElement.value = '  12   , 34  , 5  ';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual([12, 34, 5]);
    });

    it('ignores empty entries between delimiters', () => {
      input.nativeElement.value = ',  12   ,,, 3 , , 4 , ';
      input.triggerEventHandler('input', {target: input.nativeElement});
      input.triggerEventHandler('change', {target: input.nativeElement});
      fixture.detectChanges();

      expect(fixture.componentInstance.formControl.value).toEqual([12, 3, 4]);
    });
  });
});
