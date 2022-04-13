import {Component, DebugElement} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule, UntypedFormControl} from '@angular/forms';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {DurationValueAccessor} from './duration_value_accessor';
import {DurationComponentsModule} from './module';

initTestEnvironment();

@Component({template: '<input durationInput [formControl]="formControl">'})
class TestHostComponent {
  readonly formControl = new UntypedFormControl();
}

describe('DurationValueAccessor', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let input: DebugElement;

  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            DurationComponentsModule,
            ReactiveFormsModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    input = fixture.debugElement.query(By.css('input'));
  }));

  it('is applied on [durationInput]', () => {
    const el = fixture.debugElement.query(By.directive(DurationValueAccessor));
    expect(el).toBeTruthy();
  });

  it('writes formatted duration to the input value', () => {
    fixture.componentInstance.formControl.setValue('12');
    fixture.detectChanges();
    expect(input.nativeElement.value).toEqual('12 s');

    fixture.componentInstance.formControl.setValue('3600');
    fixture.detectChanges();
    expect(input.nativeElement.value).toEqual('1 h');
  });

  it('parses the duration input to a raw number', () => {
    input.nativeElement.value = '5 m';
    input.triggerEventHandler('input', {target: input.nativeElement});
    input.triggerEventHandler('change', {target: input.nativeElement});
    fixture.detectChanges();

    expect(fixture.componentInstance.formControl.value).toEqual(300);
  });
});
