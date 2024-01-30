import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatRadioButtonHarness} from '@angular/material/radio/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {
  CollectLargeFileFlowArgs,
  PathSpecPathType,
} from '../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../testing';

import {CollectLargeFileFlowForm} from './collect_large_file_flow_form';

initTestEnvironment();

describe('CollectLargeFileFlowForm', () => {
  beforeEach(waitForAsync(() => {
    return TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ReactiveFormsModule, FlowArgsFormModule],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('displays initial form', async () => {
    const fixture = TestBed.createComponent(CollectLargeFileFlowForm);
    fixture.detectChanges();

    const pathsInput = fixture.debugElement.query(
      By.css('textarea[name=path]'),
    );
    expect(pathsInput).toBeTruthy();

    const signedUrlInput = fixture.debugElement.query(
      By.css('textarea[name=signed_url]'),
    );
    expect(signedUrlInput).toBeTruthy();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const radioButtons = await harnessLoader.getAllHarnesses(
      MatRadioButtonHarness,
    );
    expect(await radioButtons[0].getLabelText()).toBe('OS');
    expect(await radioButtons[0].isChecked()).toBeTrue();
  });

  it('displays error when input is missing', () => {
    const fixture = TestBed.createComponent(CollectLargeFileFlowForm);
    fixture.detectChanges();

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error).toBeTruthy();
  });

  it('does not display error when input is present', async () => {
    const fixture = TestBed.createComponent(CollectLargeFileFlowForm);
    fixture.detectChanges();

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const pathInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: 'textarea[name=path]'}),
    );
    await pathInputHarness.setValue('/some/path');

    const signedUrlInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: 'textarea[name=signed_url]'}),
    );
    await signedUrlInputHarness.setValue('/some/url');

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error).toBeFalsy();
  });

  it('updates formValue$ output with latest form values', async () => {
    const fixture = TestBed.createComponent(CollectLargeFileFlowForm);
    fixture.detectChanges();

    let latestValue: CollectLargeFileFlowArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const pathInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: 'textarea[name=path]'}),
    );
    await pathInputHarness.setValue('/some/path');

    const signedUrlInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: 'textarea[name=signed_url]'}),
    );
    await signedUrlInputHarness.setValue('http://signed/url');

    const radioButtons = await harnessLoader.getAllHarnesses(
      MatRadioButtonHarness,
    );
    await radioButtons[1].check();

    expect(latestValue).toEqual({
      pathSpec: {path: '/some/path', pathtype: PathSpecPathType.TSK},
      signedUrl: 'http://signed/url',
    });
  });

  it('trims tabs, spaces and linebreaks in arguments', async () => {
    const fixture = TestBed.createComponent(CollectLargeFileFlowForm);
    fixture.detectChanges();

    let latestValue: CollectLargeFileFlowArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const pathInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: 'textarea[name=path]'}),
    );
    await pathInputHarness.setValue('  \n\t\n\n/acutal/path\t\n');

    const signedUrlInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: 'textarea[name=signed_url]'}),
    );
    await signedUrlInputHarness.setValue('  \n\t\n\t/acutal/path\t\n');

    expect(latestValue).toEqual({
      pathSpec: {path: '/acutal/path', pathtype: PathSpecPathType.OS},
      signedUrl: '/acutal/path',
    });
  });
});
