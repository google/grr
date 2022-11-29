import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {ReadLowLevelArgs} from '../../lib/api/api_interfaces';
import {latestValueFrom} from '../../lib/reactive';
import {initTestEnvironment} from '../../testing';

import {ReadLowLevelForm} from './read_low_level_form';

initTestEnvironment();

describe('ReadLowLevelForm', () => {
  beforeEach(waitForAsync(() => {
    return TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ReactiveFormsModule,
            FlowArgsFormModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('displays input fields', () => {
    const fixture = TestBed.createComponent(ReadLowLevelForm);
    fixture.detectChanges();

    const pathInput = fixture.debugElement.query(By.css('input[name=path]'));
    expect(pathInput).toBeTruthy();

    const lengthInput =
        fixture.debugElement.query(By.css('input[name=length]'));
    expect(lengthInput).toBeTruthy();

    const offsetInput =
        fixture.debugElement.query(By.css('input[name=offset]'));
    expect(offsetInput).toBeTruthy();
  });

  it('displays error when path and length are EMPTY', () => {
    const fixture = TestBed.createComponent(ReadLowLevelForm);
    fixture.componentInstance.controls.path.markAsTouched();
    fixture.componentInstance.controls.length.markAsTouched();
    fixture.detectChanges();

    const pathError =
        fixture.debugElement.query(By.css('mat-error[name=reqPath]'));
    expect(pathError).toBeTruthy();

    const lengthError =
        fixture.debugElement.query(By.css('mat-error[name=reqLength]'));
    expect(lengthError).toBeTruthy();
  });

  it('DOES NOT display error when path and length are NOT empty', async () => {
    const fixture = TestBed.createComponent(ReadLowLevelForm);
    fixture.detectChanges();


    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const pathInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=path]'}));
    await pathInputHarness.setValue('/some/path');
    fixture.componentInstance.controls.path.markAsTouched();
    const lengthInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=length]'}));
    await lengthInputHarness.setValue('0');
    fixture.componentInstance.controls.length.markAsTouched();
    fixture.detectChanges();

    const pathError =
        fixture.debugElement.query(By.css('mat-error[name=reqPath]'));
    expect(pathError).toBeFalsy();

    const lengthError =
        fixture.debugElement.query(By.css('mat-error[name=reqLength]'));
    expect(lengthError).toBeFalsy();
  });

  it('displays error when length is less than one', async () => {
    const fixture = TestBed.createComponent(ReadLowLevelForm);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const lengthInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=length]'}));
    await lengthInputHarness.setValue('0');
    await lengthInputHarness.blur();

    const lengthError =
        fixture.debugElement.query(By.css('mat-error[name=minLength]'));
    expect(lengthError).toBeTruthy();
  });

  it('DOES NOT display error when length is at least one', async () => {
    const fixture = TestBed.createComponent(ReadLowLevelForm);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const lengthInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=length]'}));
    await lengthInputHarness.setValue('1');
    fixture.componentInstance.controls.length.markAsTouched();
    fixture.detectChanges();

    const lengthError =
        fixture.debugElement.query(By.css('mat-error[name=minLength]'));
    expect(lengthError).toBeFalsy();
  });

  it('updates flowArgs$ output with latest value from inputs', async () => {
    const fixture = TestBed.createComponent(ReadLowLevelForm);
    fixture.detectChanges();

    let latestValue: ReadLowLevelArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const pathInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=path]'}));
    await pathInputHarness.setValue('/some/path');
    const lengthInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=length]'}));
    await lengthInputHarness.setValue('3 KiB');
    const offsetInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=offset]'}));
    await offsetInputHarness.setValue('6 B');

    expect(latestValue).toEqual({
      path: '/some/path',
      length: '3072',
      offset: '6',
    });
  });

  it('trims tabs, spaces and linebreaks in path input', async () => {
    const fixture = TestBed.createComponent(ReadLowLevelForm);
    fixture.detectChanges();

    const latestValue = latestValueFrom(fixture.componentInstance.flowArgs$);

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const pathInputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input[name=path]'}));
    await pathInputHarness.setValue('   /spaces\n\t');

    expect(latestValue.get()).toEqual(jasmine.objectContaining({
      path: '/spaces'
    }));
  });
});
