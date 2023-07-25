import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatRadioButtonHarness} from '@angular/material/radio/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {CollectFilesByKnownPathArgs, CollectFilesByKnownPathArgsCollectionLevel} from '../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../testing';

import {CollectFilesByKnownPathForm} from './collect_files_by_known_path_form';

initTestEnvironment();

describe('CollectFilesByKnownPathForm', () => {
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

  it('displays paths input', () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
    fixture.detectChanges();

    const pathsInput =
        fixture.debugElement.query(By.css('textarea[name=paths]'));
    expect(pathsInput).toBeTruthy();
  });

  it('displays error when input is EMPTY', () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
    fixture.detectChanges();

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error).toBeTruthy();
  });

  it('DOES NOT display error when input is NOT empty', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
    fixture.detectChanges();


    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const inputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'textarea[name=paths]'}));
    await inputHarness.setValue('/some/path');

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error).toBeFalsy();
  });

  it('updates formValue$ output with latest value from TEXTAREA', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
    fixture.detectChanges();

    let latestValue: CollectFilesByKnownPathArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const inputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'textarea[name=paths]'}));
    await inputHarness.setValue('/some/path');

    expect(latestValue).toEqual({
      paths: ['/some/path'],
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
    });
  });

  it('trims tabs, spaces and linebreaks in arguments', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
    fixture.detectChanges();

    let latestValue: CollectFilesByKnownPathArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const inputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'textarea[name=paths]'}));
    await inputHarness.setValue('    /spaces  \n\t/tab\n\t\n\n/after/empty');

    expect(latestValue).toEqual({
      paths: ['/spaces', '/tab', '/after/empty'],
      collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.CONTENT,
    });
  });

  it('starts with CONTENT by default', async () => {
    const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const expandButtonHarness = await harnessLoader.getHarness(
        MatButtonHarness.with({selector: '.advanced-params-button'}),
    );
    await expandButtonHarness.click();

    const radioButtons =
        await harnessLoader.getAllHarnesses(MatRadioButtonHarness);
    expect(await radioButtons[0].isChecked()).toBeTrue();
  });

  it('updates formValue$ output with latest value from RADIO BUTTONS',
     async () => {
       const fixture = TestBed.createComponent(CollectFilesByKnownPathForm);
       fixture.detectChanges();

       let latestValue: CollectFilesByKnownPathArgs = {};

       fixture.componentInstance.flowArgs$.subscribe((input) => {
         latestValue = input;
       });

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const inputHarness = await harnessLoader.getHarness(
           MatInputHarness.with({selector: 'textarea[name=paths]'}));
       await inputHarness.setValue('/some/path');

       const expandButtonHarness = await harnessLoader.getHarness(
           MatButtonHarness.with({selector: '.advanced-params-button'}),
       );
       await expandButtonHarness.click();

       const radioButtons =
           await harnessLoader.getAllHarnesses(MatRadioButtonHarness);
       await radioButtons[2].check();

       expect(latestValue).toEqual({
         paths: ['/some/path'],
         collectionLevel: CollectFilesByKnownPathArgsCollectionLevel.STAT,
       });
     });
});
