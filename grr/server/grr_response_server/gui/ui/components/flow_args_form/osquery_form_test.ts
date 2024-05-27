import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatChipGridHarness} from '@angular/material/chips/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {OsqueryFlowArgs} from '../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../testing';

import {OsqueryForm} from './osquery_form';

initTestEnvironment();

describe('OsqueryForm', () => {
  beforeEach(waitForAsync(() => {
    return TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ReactiveFormsModule, FlowArgsFormModule],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  function constructFixture(defaultFlowArgs: OsqueryFlowArgs = {}) {
    const fixture = TestBed.createComponent(OsqueryForm);
    fixture.detectChanges();
    fixture.componentInstance.resetFlowArgs(defaultFlowArgs);
    fixture.detectChanges();
    return fixture;
  }

  it('should display a code-editor,', () => {
    const fixture = constructFixture();

    const codeEditor = fixture.debugElement.query(By.css('app-code-editor'));
    expect(codeEditor).toBeTruthy();

    const browseSpecsButton = fixture.debugElement.query(
      By.css('.browse-tables-button'),
    );
    expect(browseSpecsButton).toBeTruthy();
  });

  it('should display a browse tables button,', () => {
    const fixture = constructFixture();

    const browseSpecsButton = fixture.debugElement.query(
      By.css('.browse-tables-button'),
    );
    expect(browseSpecsButton).toBeTruthy();
  });

  it('should display button for file collection settings and expand on click ', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show file collection settings.*/}),
    );
    await expandButtonHarness.click();

    const fileCollectionContainer = fixture.debugElement.query(
      By.css('.collection-container'),
    );
    expect(fileCollectionContainer).toBeTruthy();
  });

  it('should display button for low-level settings and expand on click ', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show low-level settings.*/}),
    );
    await expandButtonHarness.click();

    const lowLevelSettingsContainer = fixture.debugElement.query(
      By.css('.settings-container'),
    );
    expect(lowLevelSettingsContainer).toBeTruthy();
  });

  it('should have low-level and collection settings collapsed initially', () => {
    const fixture = constructFixture();

    const lowLevelSettingsContainer = fixture.debugElement.query(
      By.css('.settings-container'),
    );
    const collectionContainer = fixture.debugElement.query(
      By.css('.collection-container'),
    );

    expect(lowLevelSettingsContainer).toBeFalsy();

    expect(collectionContainer).toBeFalsy();
  });
  it('should have collection settings expanded when default flow args contain collection columns,', () => {
    const fixture = constructFixture({
      fileCollectionColumns: ['some column to collect files from'],
    });

    const collectionContainer = fixture.debugElement.query(
      By.css('.collection-container'),
    );
    expect(collectionContainer).toBeTruthy();
  });

  it('updates the file collection form when a value is added', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    // Here we expand the file collection settings just like the user would
    // do. At the moment of writing this, it is not strictly needed, since
    // the harnesses would find the elements even if it is collapsed.
    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show file collection settings.*/}),
    );
    await expandButtonHarness.click();

    const collectionListHarness =
      await harnessLoader.getHarness(MatChipGridHarness);

    const inputHarness = await collectionListHarness.getInput();
    await inputHarness?.setValue('column1');
    await inputHarness?.blur(); // The value is submitted on blur

    const chips = await collectionListHarness.getRows();
    const valuesInForm =
      fixture.componentInstance.controls.fileCollectionColumns.value;

    expect(chips.length).toBe(1);
    expect(valuesInForm).toEqual(['column1']);
  });

  it('updates the file collection form when a value is removed', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    // Here we expand the file collection settings just like the user would
    // do. At the moment of writing this, it is not strictly needed, since
    // the harnesses would find the elements even if it is collapsed.
    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show file collection settings.*/}),
    );
    await expandButtonHarness.click();

    const collectionListHarness =
      await harnessLoader.getHarness(MatChipGridHarness);

    const inputHarness = await collectionListHarness.getInput();
    await inputHarness?.setValue('column1');
    await inputHarness?.blur(); // The value is submitted on blur

    const chips = await collectionListHarness.getRows();
    expect(chips.length).toBe(1);

    await chips[0].remove();
    const chipsAfterRemoval = await collectionListHarness.getRows();
    const valuesInFormAfterRemoval =
      fixture.componentInstance.form.controls.fileCollectionColumns.value;

    expect(chipsAfterRemoval.length).toBe(0);
    expect(valuesInFormAfterRemoval.length).toBe(0);
  });

  it('should not add any content path or content configuration', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    let latestValue: OsqueryFlowArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show low-level settings.*/}),
    );
    await expandButtonHarness.click();

    // Child form components are populated with the patched values
    fixture.detectChanges();

    const configPathInput = fixture.debugElement.query(
      By.css('input[name=configurationPath]'),
    );
    expect(configPathInput.nativeElement.value).toBe('');
    const configContentInput = fixture.debugElement.query(
      By.css('textarea[name=configurationContent]'),
    );
    expect(configContentInput.nativeElement.value).toBe('');

    expect(latestValue).toEqual({});
  });

  it('shows a warning when configuration path contains %%', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show low-level settings.*/}),
    );
    await expandButtonHarness.click();

    const configPathInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: '[name=configurationPath]'}),
    );
    await configPathInputHarness?.setValue('%%');
    await configPathInputHarness?.blur();
    fixture.detectChanges();

    const configPathInput = fixture.debugElement.query(
      By.css('input[name=configurationPath]'),
    );
    expect(configPathInput.nativeElement.value).toBe('%%');
    const pathKnowledgebaseExpressionWarning = fixture.debugElement.query(
      By.css('app-literal-knowledgebase-expression-warning span'),
    );
    expect(
      pathKnowledgebaseExpressionWarning.nativeElement.innerText,
    ).toContain('path uses %% literally');
  });

  it('shows a warning when both configuration path and content are set', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show low-level settings.*/}),
    );
    await expandButtonHarness.click();

    const configPathInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: '[name=configurationPath]'}),
    );
    await configPathInputHarness?.setValue('/some/path');
    await configPathInputHarness?.blur();
    fixture.detectChanges();

    const configContentInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: '[name=configurationContent]'}),
    );
    await configContentInputHarness?.setValue('{}');
    await configContentInputHarness?.blur();
    fixture.detectChanges();

    const configPathInput = fixture.debugElement.query(
      By.css('input[name=configurationPath]'),
    );
    expect(configPathInput.nativeElement.value).toBe('/some/path');
    const configContentInput = fixture.debugElement.queryAll(
      By.css('textarea[name=configurationContent]'),
    );
    expect(configContentInput[0].nativeElement.value).toBe('{}');
    const matError = fixture.debugElement.query(By.css('mat-error'));
    expect(matError.nativeElement.innerText).toContain(
      'Only one of configuration content or configuration path can be set',
    );
  });

  it('should add content path', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    let latestValue: OsqueryFlowArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show low-level settings.*/}),
    );
    await expandButtonHarness.click();

    const configPathInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: '[name=configurationPath]'}),
    );
    await configPathInputHarness?.setValue('/some/path/config.json');
    await configPathInputHarness?.blur();
    fixture.detectChanges();

    const configPathInput = fixture.debugElement.query(
      By.css('input[name=configurationPath]'),
    );
    expect(configPathInput.nativeElement.value).toBe('/some/path/config.json');
    const configContentInput = fixture.debugElement.query(
      By.css('textarea[name=configurationContent]'),
    );
    expect(configContentInput.nativeElement.value).toBe('');

    expect(latestValue).toEqual({
      configurationPath: '/some/path/config.json',
      configurationContent: '',
      query: 'SELECT * FROM users LIMIT 10;',
      timeoutMillis: '0',
      ignoreStderrErrors: false,
      fileCollectionColumns: [],
    });
  });

  it('should add content configuration', async () => {
    const fixture = constructFixture();
    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);

    let latestValue: OsqueryFlowArgs = {};

    fixture.componentInstance.flowArgs$.subscribe((input) => {
      latestValue = input;
    });

    const expandButtonHarness = await harnessLoader.getHarness(
      MatButtonHarness.with({text: /Show low-level settings.*/}),
    );
    await expandButtonHarness.click();

    const configContentInputHarness = await harnessLoader.getHarness(
      MatInputHarness.with({selector: '[name=configurationContent]'}),
    );
    await configContentInputHarness?.setValue('{}');
    await configContentInputHarness?.blur();
    fixture.detectChanges();

    const configPathInput = fixture.debugElement.query(
      By.css('input[name=configurationPath]'),
    );
    expect(configPathInput.nativeElement.value).toBe('');
    const configContentInput = fixture.debugElement.query(
      By.css('textarea[name=configurationContent]'),
    );
    expect(configContentInput.nativeElement.value).toBe('{}');

    expect(latestValue).toEqual({
      configurationPath: '',
      configurationContent: '{}',
      query: 'SELECT * FROM users LIMIT 10;',
      timeoutMillis: '0',
      ignoreStderrErrors: false,
      fileCollectionColumns: [],
    });
  });
});
