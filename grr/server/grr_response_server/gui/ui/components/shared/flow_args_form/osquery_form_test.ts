import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {OsqueryFlowArgs} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {OsqueryForm} from './osquery_form';
import {OsqueryFormHarness} from './testing/osquery_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(OsqueryForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    OsqueryFormHarness,
  );
  return {fixture, harness};
}

describe('Osquery Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [OsqueryForm, NoopAnimationsModule],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('triggers onSubmit callback when submitting the form', async () => {
    const {harness, fixture} = await createComponent();
    let onSubmitCalled = false;
    fixture.componentRef.setInput(
      'onSubmit',
      (flowName: string, flowArgs: object) => {
        expect(flowName).toBe('OsqueryFlow');
        expect(flowArgs).toEqual({
          query: 'SELECT * FROM grr LIMIT 10;',
          timeoutMillis: '10000',
          ignoreStderrErrors: true,
          fileCollectionColumns: ['a', 'b', 'c'],
          configurationPath: '/any/path',
          configurationContent: '',
        });
        onSubmitCalled = true;
      },
    );

    await harness.setQuery('SELECT * FROM grr LIMIT 10;');

    const fileCollectionSettingsButton =
      await harness.fileCollectionSettingsButton();
    await fileCollectionSettingsButton!.click();
    await harness.setFileCollectionColumns(['a', 'b', 'c']);
    fixture.detectChanges();

    const lowLevelSettingsButton = await harness.lowLevelSettingsButton();
    await lowLevelSettingsButton!.click();

    await harness.setTimeout('10000');

    const ignoreStderrErrorsCheckbox =
      await harness.ignoreStderrErrorsCheckbox();
    await ignoreStderrErrorsCheckbox!.check();

    await harness.setConfigurationPath('/any/path');
    await harness.setConfigurationContent('');

    const submitButton = await harness.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      query: 'SELECT * FROM grr LIMIT 10;',
      timeoutMillis: 10000,
      ignoreStderrErrors: false,
      fileCollectionColumns: ['a', 'b', 'c'],
      configurationPath: '/any/path',
      configurationContent: '',
    });

    const expectedFlowArgs: OsqueryFlowArgs = {
      query: 'SELECT * FROM grr LIMIT 10;',
      timeoutMillis: '10000',
      ignoreStderrErrors: false,
      fileCollectionColumns: ['a', 'b', 'c'],
      configurationPath: '/any/path',
      configurationContent: '',
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: OsqueryFlowArgs = {
      query: 'SELECT * FROM grr LIMIT 10;',
      timeoutMillis: '10000',
      ignoreStderrErrors: false,
      fileCollectionColumns: ['a', 'b', 'c'],
      configurationPath: '',
      configurationContent: 'any content =)',
    };

    expect(
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs),
    ).toEqual({
      query: 'SELECT * FROM grr LIMIT 10;',
      timeoutMillis: 10000,
      ignoreStderrErrors: false,
      fileCollectionColumns: ['a', 'b', 'c'],
      configurationPath: '',
      configurationContent: 'any content =)',
    });
  });

  it('resets the flow args when resetFlowArgs is called', async () => {
    const {harness} = await createComponent({
      query: 'SELECT * FROM grr LIMIT 10;',
      timeoutMillis: '10000',
      ignoreStderrErrors: true,
      fileCollectionColumns: ['a', 'b', 'c'],
      configurationPath: '',
      configurationContent: 'any content =)',
    });

    expect(await harness.getQuery()).toBe('SELECT * FROM grr LIMIT 10;');
    expect(await harness.getTimeout()).toBe('10000');
    expect(await harness.getFileCollectionColumns()).toEqual(['a', 'b', 'c']);
    expect(await harness.getConfigurationPath()).toBe('');
    expect(await harness.getConfigurationContent()).toBe('any content =)');
    const stdErrorCheckbox = await harness.ignoreStderrErrorsCheckbox();
    expect(await stdErrorCheckbox!.isChecked()).toBeTrue();
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('should display a browse tables button,', async () => {
    const {harness} = await createComponent();
    const browseTablesButton = await harness.browseTablesButton();
    expect(browseTablesButton).toBeDefined();
  });

  it('can expand and hide file collection settings', async () => {
    const {harness} = await createComponent();

    expect(await harness.hasFileCollectionFormField()).toBeFalse();

    const fileCollectionSettingsButton =
      await harness.fileCollectionSettingsButton();
    await fileCollectionSettingsButton!.click();

    expect(await harness.hasFileCollectionFormField()).toBeTrue();

    const hideFileCollectionSettinsButton =
      await harness.hideFileCollectionSettingsButton();
    await hideFileCollectionSettinsButton!.click();

    expect(await harness.hasFileCollectionFormField()).toBeFalse();
  });

  it('can expand and hide low-level settings', async () => {
    const {harness} = await createComponent();

    expect(await harness.hasTimeout()).toBeFalse();

    const lowLevelSettingsButton = await harness.lowLevelSettingsButton();
    await lowLevelSettingsButton!.click();

    expect(await harness.hasTimeout()).toBeTrue();

    const hideLowLevelSettingsButton =
      await harness.hideLowLevelSettingsButton();
    await hideLowLevelSettingsButton!.click();

    expect(await harness.hasTimeout()).toBeFalse();
  });

  it('updates the file collection form when a value is added', async () => {
    const {harness} = await createComponent();

    const fileCollectionSettingsButton =
      await harness.fileCollectionSettingsButton();
    await fileCollectionSettingsButton!.click();

    expect(await harness.getFileCollectionColumns()).toEqual([]);

    await harness.setFileCollectionColumns(['column1']);

    expect(await harness.getFileCollectionColumns()).toEqual(['column1']);
  });

  it('updates the file collection form when a value is removed', async () => {
    const {harness} = await createComponent();

    const fileCollectionSettingsButton =
      await harness.fileCollectionSettingsButton();
    await fileCollectionSettingsButton!.click();

    await harness.setFileCollectionColumns(['column1']);

    const chips = await harness.getFileCollectionChips();
    expect(chips.length).toBe(1);
    await chips[0].remove();

    expect(await harness.getFileCollectionColumns()).toEqual([]);
  });

  it('should be initialized with empty content path and configuration', async () => {
    const {harness} = await createComponent();

    const lowLevelSettingsButton = await harness.lowLevelSettingsButton();
    await lowLevelSettingsButton!.click();

    expect(await harness.getConfigurationPath()).toBe('');
    expect(await harness.getConfigurationContent()).toBe('');
  });

  it('shows a warning when configuration path contains %%', async () => {
    const {harness} = await createComponent();

    const lowLevelSettingsButton = await harness.lowLevelSettingsButton();
    await lowLevelSettingsButton!.click();

    await harness.setConfigurationPath('%%');

    expect(await harness.getConfigurationPathWarnings()).toEqual([
      'This path uses `%%` literally and will not evaluate any `%%knowledgebase_expressions%%`.',
    ]);
  });
});
