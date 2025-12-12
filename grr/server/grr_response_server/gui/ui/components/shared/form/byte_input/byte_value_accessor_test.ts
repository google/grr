import {Component, DebugElement} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule, UntypedFormControl} from '@angular/forms';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';
import {ByteValueAccessor} from './byte_value_accessor';

initTestEnvironment();

@Component({
  template: '<input byteInput [formControl]="formControl">',
  imports: [ByteValueAccessor, ReactiveFormsModule],
})
class TestHostComponent {
  readonly formControl = new UntypedFormControl();
}

describe('ByteValueAccessor', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let input: DebugElement;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ByteValueAccessor],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    input = fixture.debugElement.query(By.css('input'));
  }));

  it('is applied on [byteInput]', () => {
    const el = fixture.debugElement.query(By.directive(ByteValueAccessor));
    expect(el).toBeTruthy();
  });

  it('writes formatted bytes to the input value', () => {
    fixture.componentInstance.formControl.setValue('1111');
    fixture.detectChanges();
    expect(input.nativeElement.value).toEqual('1111 B');

    fixture.componentInstance.formControl.setValue('1024');
    fixture.detectChanges();
    expect(input.nativeElement.value).toEqual('1 KiB');
  });

  it('parses the byte input to a raw number', () => {
    input.nativeElement.value = '2 KiB';
    input.triggerEventHandler('input', {target: input.nativeElement});
    input.triggerEventHandler('change', {target: input.nativeElement});
    fixture.detectChanges();

    expect(fixture.componentInstance.formControl.value).toEqual(2048);
  });
});
