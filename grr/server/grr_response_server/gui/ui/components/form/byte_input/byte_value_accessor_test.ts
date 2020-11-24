import {Component, DebugElement} from '@angular/core';
import {async, ComponentFixture, TestBed} from '@angular/core/testing';
import {FormControl} from '@angular/forms';
import {ReactiveFormsModule} from '@angular/forms';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {ByteValueAccessor} from './byte_value_accessor';
import {ByteComponentsModule} from './module';


initTestEnvironment();

@Component({template: '<input byteInput [formControl]="formControl">'})
class TestHostComponent {
  readonly formControl = new FormControl();
}

describe('ByteValueAccessor', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let input: DebugElement;

  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ByteComponentsModule,
            ReactiveFormsModule,
          ],
          declarations: [
            TestHostComponent,
          ],

          providers: []
        })
        .compileComponents();

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
