import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatInputModule} from '@angular/material/input';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../../testing';
import {DurationValueAccessor} from './duration_value_accessor';

initTestEnvironment();

@Component({
  template: `
      <mat-form-field>
        <input durationInput matInput [(ngModel)]="inputValue" />
      </mat-form-field>`,
  imports: [
    DurationValueAccessor,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    ReactiveFormsModule,
  ],
})
class TestHostComponent {
  inputValue: number | undefined = undefined;
}

describe('Duration Value Accessor', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let input: MatInputHarness;

  beforeEach(waitForAsync(async () => {
    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, TestHostComponent],
      teardown: {destroyAfterEach: true},
    }).compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    input = (await loader.getAllHarnesses(MatInputHarness))[0];
    fixture.detectChanges();
  }));

  it('is applied on [durationInput]', () => {
    const el = fixture.debugElement.query(By.directive(DurationValueAccessor));
    expect(el).toBeTruthy();
  });

  it('writes formatted duration to the input value', async () => {
    fixture.componentInstance.inputValue = 12;
    expect(await input.getValue()).toEqual('12 s');

    fixture.componentInstance.inputValue = 3600;
    expect(await input.getValue()).toEqual('1 h');
  });

  it('parses the duration input to a raw number', async () => {
    await input.setValue('12 s');
    expect(fixture.componentInstance.inputValue).toEqual(12);

    await input.setValue('1h');
    expect(fixture.componentInstance.inputValue).toEqual(3600);
  });
});
