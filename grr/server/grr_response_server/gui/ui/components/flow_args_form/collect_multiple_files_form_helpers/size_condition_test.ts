import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ControlContainer} from '@angular/forms';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {HelpersModule} from './module';
import {createSizeFormGroup, SizeCondition} from './size_condition';

initTestEnvironment();

describe('SizeCondition component', () => {
  let control: ReturnType<typeof createSizeFormGroup>;
  let controlContainer: Partial<ControlContainer>;

  beforeEach(waitForAsync(() => {
    control = createSizeFormGroup();
    controlContainer = {control};

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
          ],
          providers: [
            {
              provide: ControlContainer,
              useFactory: () => controlContainer,
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('displays correctly filled min and max file size fields when initialized',
     () => {
       const fixture = TestBed.createComponent(SizeCondition);
       fixture.detectChanges();

       const [minField, maxField] =
           fixture.debugElement.queryAll(By.css('input'));
       expect(minField.nativeElement.value).toBe('');
       expect(maxField.nativeElement.value).toBe('20 MB');
     });

  it('exposes form values and shows currect hint when only minimum file size field is filled',
     async () => {
       const fixture = TestBed.createComponent(SizeCondition);
       const loader = TestbedHarnessEnvironment.loader(fixture);
       fixture.detectChanges();

       const minFileSizeHarness = await loader.getHarness(
           MatInputHarness.with({selector: '[name="minFileSize"]'}));
       const maxFileSizeHarness = await loader.getHarness(
           MatInputHarness.with({selector: '[name="maxFileSize"]'}));
       await minFileSizeHarness.setValue('10 MB');
       await maxFileSizeHarness.setValue('');

       expect(control.value).toEqual(jasmine.objectContaining({
         minFileSize: 10_000_000
       }));

       const matHintField = fixture.debugElement.query(By.css('mat-hint'));
       expect(matHintField.nativeElement.textContent.trim())
           .toEqual(
               'Will collect files of size at least 10 megabytes = ' +
               '10,000,000 bytes, inclusive');
     });

  it('exposes form values and shows currect hint when both fields are filled',
     async () => {
       const fixture = TestBed.createComponent(SizeCondition);
       const loader = TestbedHarnessEnvironment.loader(fixture);
       fixture.detectChanges();

       const minFileSizeHarness = await loader.getHarness(
           MatInputHarness.with({selector: '[name="minFileSize"]'}));
       const maxFileSizeHarness = await loader.getHarness(
           MatInputHarness.with({selector: '[name="maxFileSize"]'}));
       await minFileSizeHarness.setValue('10 MB');
       await maxFileSizeHarness.setValue('10 GiB');

       expect(control.value).toEqual({
         minFileSize: 10_000_000,
         maxFileSize: 10_737_418_240,
       });

       const matHintField = fixture.debugElement.query(By.css('mat-hint'));
       expect(matHintField.nativeElement.textContent.trim())
           .toEqual(
               'Will collect files of size at least 10 megabytes = ' +
               '10,000,000 bytes and at most 10 gibibytes = ' +
               '10,737,418,240 bytes, inclusive');
     });

  it('correctly ignores input value of 0', async () => {
    const fixture = TestBed.createComponent(SizeCondition);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();

    const minFileSizeHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[name="minFileSize"]'}));
    const maxFileSizeHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[name="maxFileSize"]'}));
    await minFileSizeHarness.setValue('0');
    await maxFileSizeHarness.setValue('2 GiB');

    expect(control.value).toEqual({
      minFileSize: 0,
      maxFileSize: 2_147_483_648,
    });

    const matHintField = fixture.debugElement.query(By.css('mat-hint'));
    expect(matHintField.nativeElement.textContent.trim())
        .toEqual(
            'Will collect files of size at most 2 gibibytes = ' +
            '2,147,483,648 bytes, inclusive');
  });

  it('surfaces error message when neither fields are filled', async () => {
    const fixture = TestBed.createComponent(SizeCondition);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();

    const minFileSizeHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[name="minFileSize"]'}));
    const maxFileSizeHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[name="maxFileSize"]'}));
    await minFileSizeHarness.setValue('');
    await maxFileSizeHarness.setValue('');

    const matHintField = fixture.debugElement.query(By.css('mat-hint'));
    expect(matHintField).toBeFalsy();

    const matErrorField = fixture.debugElement.query(By.css('mat-error'));
    expect(matErrorField.nativeElement.textContent.trim())
        .toEqual('Either one or both values must be set.');
  });
});
