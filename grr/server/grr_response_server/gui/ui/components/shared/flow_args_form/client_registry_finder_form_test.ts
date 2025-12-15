import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  FileFinderContentsLiteralMatchConditionMode,
  FileFinderContentsRegexMatchConditionMode,
  RegistryFinderArgs,
  RegistryFinderConditionType,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {ClientRegistryFinderForm} from './client_registry_finder_form';
import {ClientRegistryFinderFormHarness} from './testing/client_registry_finder_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(ClientRegistryFinderForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientRegistryFinderFormHarness,
  );
  return {fixture, harness};
}

describe('Client Registry Finder Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ClientRegistryFinderForm, NoopAnimationsModule],
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
        expect(flowName).toBe('ClientRegistryFinder');
        expect(flowArgs).toEqual({
          keysPaths: ['/some/path'],
          conditions: [
            {
              conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
              valueLiteralMatch: {
                literal: btoa('test'),
                mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
              },
            },
            {
              conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
              valueRegexMatch: {
                regex: btoa('test'),
                mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
                length: '30000000',
              },
            },
            {
              conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
              modificationTime: {
                minLastModifiedTime: '1704114000000000',
                maxLastModifiedTime: '1704115800000000',
              },
            },
            {
              conditionType: RegistryFinderConditionType.SIZE,
              size: {
                minFileSize: '10000000',
                maxFileSize: '20000000',
              },
            },
          ],
        });
        onSubmitCalled = true;
      },
    );
    const globExpressionInputs = await harness.globExpressionInputs();
    const globExpressionInput = await globExpressionInputs[0].input();
    await globExpressionInput.setValue('/some/path');

    const literalMatchFilterButton =
      await harness.addLiteralMatchFilterButton();
    await literalMatchFilterButton.click();
    const literalMatchSubform = (await harness.literalMatchSubforms())[0];
    const literalInput = await literalMatchSubform!.literalInput();
    await literalInput.setValue('test');
    const literalModeSelect = await literalMatchSubform!.modeSelect();
    await literalModeSelect.clickOptions({text: 'All Hits'});

    const regexMatchFilterButton = await harness.addRegexMatchFilterButton();
    await regexMatchFilterButton.click();
    const regexMatchSubform = (await harness.regexMatchSubforms())[0];
    const regexInput = await regexMatchSubform!.regexInput();
    await regexInput.setValue('test');
    const regexModeSelect = await regexMatchSubform!.modeSelect();
    await regexModeSelect.clickOptions({text: 'All Hits'});
    const lengthInput = await regexMatchSubform!.lengthInput();
    await lengthInput.setValue('30000000');

    const modificationTimeFilterButton =
      await harness.addModificationTimeFilterButton();
    await modificationTimeFilterButton.click();
    const modificationTimeSubform = (
      await harness.modificationTimeSubforms()
    )[0];
    const fromModificationTime = await modificationTimeSubform!.fromDateInput();
    await fromModificationTime.setValue('01/01/2024 1:00 PM UTC');
    const toModificationTime = await modificationTimeSubform!.toDateInput();
    await toModificationTime.setValue('01/01/2024 1:30 PM UTC');

    const fileSizeFilterButton = await harness.addFileSizeFilterButton();
    await fileSizeFilterButton.click();
    const fileSizeSubform = (await harness.fileSizeSubforms())[0];
    const fileSizeInput = await fileSizeSubform!.minFileSizeInput();
    await fileSizeInput.setValue('10000000 B');

    const submitButton = await harness.getSubmitButton();

    await submitButton.submit();
    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      keysPaths: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      valueLiteralMatches: [
        {
          literal: 'test',
          mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
        },
        {
          literal: 'test2',
          mode: FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
        },
      ],
      valueRegexMatches: [
        {
          regex: 'test',
          mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
          length: 30000000,
        },
        {
          regex: 'test2',
          mode: FileFinderContentsRegexMatchConditionMode.FIRST_HIT,
          length: 10000000,
        },
      ],
      modificationTimes: [
        {
          fromTime: new Date('2024-01-01T13:00:00Z'),
          toTime: new Date('2024-01-01T13:30:00Z'),
        },
        {
          fromTime: new Date('2024-01-01T13:45:00Z'),
          toTime: new Date('2024-01-01T14:15:00Z'),
        },
      ],
      sizes: [
        {
          minFileSize: 100,
          maxFileSize: 200,
        },
        {
          minFileSize: 300,
          maxFileSize: 400,
        },
      ],
    });
    const expectedFlowArgs: RegistryFinderArgs = {
      keysPaths: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      conditions: [
        {
          conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
          valueLiteralMatch: {
            literal: btoa('test'),
            mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
          },
        },
        {
          conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
          valueLiteralMatch: {
            literal: btoa('test2'),
            mode: FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
          },
        },
        {
          conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
          valueRegexMatch: {
            regex: btoa('test'),
            mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
            length: '30000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
          valueRegexMatch: {
            regex: btoa('test2'),
            mode: FileFinderContentsRegexMatchConditionMode.FIRST_HIT,
            length: '10000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
          modificationTime: {
            minLastModifiedTime: '1704114000000000',
            maxLastModifiedTime: '1704115800000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
          modificationTime: {
            minLastModifiedTime: '1704116700000000',
            maxLastModifiedTime: '1704118500000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.SIZE,
          size: {
            minFileSize: '100',
            maxFileSize: '200',
          },
        },
        {
          conditionType: RegistryFinderConditionType.SIZE,
          size: {
            minFileSize: '300',
            maxFileSize: '400',
          },
        },
      ],
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: RegistryFinderArgs = {
      keysPaths: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      conditions: [
        {
          conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
          valueLiteralMatch: {
            literal: btoa('test'),
            mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
          },
        },
        {
          conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
          valueLiteralMatch: {
            literal: btoa('test2'),
            mode: FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
          },
        },
        {
          conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
          valueRegexMatch: {
            regex: btoa('test'),
            mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
            length: '30000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
          valueRegexMatch: {
            regex: btoa('test2'),
            mode: FileFinderContentsRegexMatchConditionMode.FIRST_HIT,
            length: '10000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
          modificationTime: {
            minLastModifiedTime: '1704114000000000',
            maxLastModifiedTime: '1704115800000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
          modificationTime: {
            minLastModifiedTime: '1704116700000000',
            maxLastModifiedTime: '1704118500000000',
          },
        },
        {
          conditionType: RegistryFinderConditionType.SIZE,
          size: {
            minFileSize: '100',
            maxFileSize: '200',
          },
        },
        {
          conditionType: RegistryFinderConditionType.SIZE,
          size: {
            minFileSize: '300',
            maxFileSize: '400',
          },
        },
      ],
    };
    const formState =
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs);

    expect(formState).toEqual({
      keysPaths: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      valueLiteralMatches: [
        {
          literal: 'test',
          mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
        },
        {
          literal: 'test2',
          mode: FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
        },
      ],
      valueRegexMatches: [
        {
          regex: 'test',
          mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
          length: 30000000,
        },
        {
          regex: 'test2',
          mode: FileFinderContentsRegexMatchConditionMode.FIRST_HIT,
          length: 10000000,
        },
      ],
      modificationTimes: [
        {
          fromTime: new Date('2024-01-01T13:00:00Z'),
          toTime: new Date('2024-01-01T13:30:00Z'),
        },
        {
          fromTime: new Date('2024-01-01T13:45:00Z'),
          toTime: new Date('2024-01-01T14:15:00Z'),
        },
      ],
      sizes: [
        {
          minFileSize: 100,
          maxFileSize: 200,
        },
        {
          minFileSize: 300,
          maxFileSize: 400,
        },
      ],
    });
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('initializes one empty path expression by default', async () => {
    const {harness} = await createComponent();

    expect(await harness.globExpressionInputs()).toHaveSize(1);
    const globExpression = (await harness.globExpressionInputs())[0];
    const globExpressionInput = await globExpression.input();
    expect(await globExpressionInput.getValue()).toBe('');
  });

  it('does not show a warning when the path expression does not use /', async () => {
    const {harness} = await createComponent();

    const globExpression = (await harness.globExpressionInputs())[0];
    const globExpressionInput = await globExpression.input();
    await globExpressionInput.setValue('\\valid\\windows\\path');
    await globExpressionInput.blur();

    const windowsPathWarnings = await harness.windowsPathWarnings();
    expect(windowsPathWarnings).toHaveSize(1);
    expect(await windowsPathWarnings[0].warnings()).toHaveSize(0);
  });

  it('shows a warning when the path expression uses / instead of \\', async () => {
    const {harness} = await createComponent();

    const globExpression = (await harness.globExpressionInputs())[0];
    const globExpressionInput = await globExpression.input();
    await globExpressionInput.setValue('/some/path');
    await globExpressionInput.blur();

    const windowsPathWarnings = await harness.windowsPathWarnings();
    expect(windowsPathWarnings).toHaveSize(1);
    expect(await windowsPathWarnings[0].warnings()).toHaveSize(1);
    expect(await windowsPathWarnings[0].getWarningMessages()).toEqual([
      'Windows path use `\\` instead of `/`.',
    ]);
  });

  it('adds path expression', async () => {
    const {harness} = await createComponent();

    const addPathExpressionButton = await harness.addPathExpressionButton();
    await addPathExpressionButton.click();
    await addPathExpressionButton.click();

    const newGlobExpressionInputs = await harness.globExpressionInputs();
    expect(newGlobExpressionInputs).toHaveSize(3);
  });

  it('removes path expression', async () => {
    const {harness} = await createComponent();

    await harness.removePathExpression(0);

    const newGlobExpressionInputs = await harness.globExpressionInputs();
    expect(newGlobExpressionInputs).toHaveSize(0);
  });

  it('initially has no filter conditions', async () => {
    const {harness} = await createComponent();

    expect(await harness.numLiteralMatchSubforms()).toBe(0);
    expect(await harness.numRegexMatchSubforms()).toBe(0);
    expect(await harness.numModificationTimeSubforms()).toBe(0);
    expect(await harness.numFileSizeSubforms()).toBe(0);
  });

  it('adds literal match form', async () => {
    const {harness} = await createComponent();

    const literalMatchFilterButton =
      await harness.addLiteralMatchFilterButton();
    await literalMatchFilterButton.click();
    await literalMatchFilterButton.click();

    expect(await harness.numLiteralMatchSubforms()).toBe(2);
  });

  it('removes literal match form', async () => {
    const {harness} = await createComponent();

    const literalMatchFilterButton =
      await harness.addLiteralMatchFilterButton();
    await literalMatchFilterButton.click();
    await harness.removeLiteralMatchFilter(0);

    expect(await harness.numLiteralMatchSubforms()).toBe(0);
  });

  it('adds regex match form', async () => {
    const {harness} = await createComponent();

    const regexMatchFilterButton = await harness.addRegexMatchFilterButton();
    await regexMatchFilterButton.click();
    await regexMatchFilterButton.click();

    expect(await harness.numRegexMatchSubforms()).toBe(2);
  });

  it('removes regex match form', async () => {
    const {harness} = await createComponent();

    const regexMatchFilterButton = await harness.addRegexMatchFilterButton();
    await regexMatchFilterButton.click();
    await harness.removeRegexMatchFilter(0);

    expect(await harness.numLiteralMatchSubforms()).toBe(0);
  });

  it('adds modification time form', async () => {
    const {harness} = await createComponent();

    const modificationTimeFilterButton =
      await harness.addModificationTimeFilterButton();
    await modificationTimeFilterButton.click();
    await modificationTimeFilterButton.click();

    expect(await harness.numModificationTimeSubforms()).toBe(2);
  });

  it('removes modification time form', async () => {
    const {harness} = await createComponent();

    const modificationTimeFilterButton =
      await harness.addModificationTimeFilterButton();
    await modificationTimeFilterButton.click();
    await harness.removeModificationTimeFilter(0);

    expect(await harness.numModificationTimeSubforms()).toBe(0);
  });

  it('adds file size form', async () => {
    const {harness} = await createComponent();

    const fileSizeFilterButton = await harness.addFileSizeFilterButton();
    await fileSizeFilterButton.click();
    await fileSizeFilterButton.click();

    expect(await harness.numFileSizeSubforms()).toBe(2);
  });

  it('removes file size form', async () => {
    const {harness} = await createComponent();

    const fileSizeFilterButton = await harness.addFileSizeFilterButton();
    await fileSizeFilterButton.click();
    await harness.removeFileSizeFilter(0);

    expect(await harness.numFileSizeSubforms()).toBe(0);
  });

  describe('Initialization with fixed flow args', () => {
    it('initializes empty path expression', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        keysPaths: [],
        conditions: [],
      };
      const {harness} = await createComponent(testFlowArgs);

      const globExpressionInputs = await harness.globExpressionInputs();
      expect(globExpressionInputs).toHaveSize(1);
      const globExpressionInput = await globExpressionInputs[0].input();
      expect(await globExpressionInput.getValue()).toBe('');
      expect(await harness.numRegexMatchSubforms()).toBe(0);
      expect(await harness.numLiteralMatchSubforms()).toBe(0);
      expect(await harness.numModificationTimeSubforms()).toBe(0);
      expect(await harness.numFileSizeSubforms()).toBe(0);
    });

    it('should initialize path expressions', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        keysPaths: ['expressionTest1', 'expressionTest2'],
      };
      const {harness} = await createComponent(testFlowArgs);

      const globExpressionInputs = await harness.globExpressionInputs();
      expect(globExpressionInputs).toHaveSize(2);

      const globExpressionInput0 = await globExpressionInputs[0].input();
      const globExpressionInput1 = await globExpressionInputs[1].input();

      expect(await globExpressionInput0.getValue()).toBe('expressionTest1');
      expect(await globExpressionInput1.getValue()).toBe('expressionTest2');
    });

    it('should initialize one empty path expression when keysPaths is undefined', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        keysPaths: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);

      const globExpressionInputs = await harness.globExpressionInputs();
      expect(globExpressionInputs).toHaveSize(1);
      const globExpressionInput = await globExpressionInputs[0].input();
      expect(await globExpressionInput.getValue()).toBe('');
    });

    it('initializes a regex match condition', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
            valueRegexMatch: {
              regex: btoa('test'),
              mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
              length: '20000000',
            },
          },
        ],
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.numRegexMatchSubforms()).toBe(1);
      const regexMatchSubform = (await harness.regexMatchSubforms())[0];
      const regexInput = await regexMatchSubform!.regexInput();
      expect(await regexInput.getValue()).toBe('test');
      const lengthInput = await regexMatchSubform!.lengthInput();
      expect(await lengthInput.getValue()).toBe('20000000');
      const regexModeSelect = await regexMatchSubform!.modeSelect();
      expect(await regexModeSelect.getValueText()).toBe('All Hits');
    });

    it('hides regex match condition when undefined', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
            valueRegexMatch: undefined,
          },
        ],
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.numRegexMatchSubforms()).toBe(0);
    });

    it('initializes a literal match condition', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
            valueLiteralMatch: {
              literal: btoa('test'),
              mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
            },
          },
        ],
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.numLiteralMatchSubforms()).toBe(1);
      const literalMatchSubform = (await harness.literalMatchSubforms())[0];
      const literalInput = await literalMatchSubform!.literalInput();
      expect(await literalInput.getValue()).toBe('test');
      const literalModeSelect = await literalMatchSubform!.modeSelect();
      expect(await literalModeSelect.getValueText()).toBe('All Hits');
    });

    it('hides a literal match condition when undefined', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
            valueLiteralMatch: undefined,
          },
        ],
      };

      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.numLiteralMatchSubforms()).toBe(0);
    });

    it('initializes a modification time condition', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
            modificationTime: {
              minLastModifiedTime: '4242000000',
              maxLastModifiedTime: '4343000000',
            },
          },
        ],
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.numModificationTimeSubforms()).toBe(1);
      const modificationTimeSubform = (
        await harness.modificationTimeSubforms()
      )[0];
      expect(await modificationTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );
      expect(await modificationTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );
    });

    it('hides a modification time condition when undefined', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
            modificationTime: undefined,
          },
        ],
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.numModificationTimeSubforms()).toBe(0);
    });

    it('should show a file size condition', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.SIZE,
            size: {
              minFileSize: '10000',
              maxFileSize: '20000000',
            },
          },
        ],
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.numFileSizeSubforms()).toBe(1);
      const sizeSubform = (await harness.fileSizeSubforms())[0];
      const minFileSizeInput = await sizeSubform!.minFileSizeInput();
      expect(await minFileSizeInput.getValue()).toBe('10 kB');
      const maxFileSizeInput = await sizeSubform!.maxFileSizeInput();
      expect(await maxFileSizeInput.getValue()).toBe('20 MB');
    });

    it('hides file size condition when undefined', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        conditions: [
          {
            conditionType: RegistryFinderConditionType.SIZE,
            size: undefined,
          },
        ],
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.numFileSizeSubforms()).toBe(0);
    });

    it('can add multiple form elements', async () => {
      const testFlowArgs: RegistryFinderArgs = {
        keysPaths: ['expressionTest1'],
        conditions: [
          {
            conditionType: RegistryFinderConditionType.VALUE_REGEX_MATCH,
            valueRegexMatch: {
              regex: btoa('test'),
              mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
              length: '20000000',
            },
          },
          {
            conditionType: RegistryFinderConditionType.VALUE_LITERAL_MATCH,
            valueLiteralMatch: {
              literal: btoa('test'),
              mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
            },
          },
          {
            conditionType: RegistryFinderConditionType.MODIFICATION_TIME,
            modificationTime: {
              minLastModifiedTime: '4242000000',
              maxLastModifiedTime: '4343000000',
            },
          },
          {
            conditionType: RegistryFinderConditionType.SIZE,
            size: {
              minFileSize: '10000',
              maxFileSize: '20000000',
            },
          },
        ],
      };

      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.globExpressionInputs()).toHaveSize(1);
      const globExpressionInputs = await harness.globExpressionInputs();
      const globExpressionInput0 = await globExpressionInputs[0].input();
      expect(await globExpressionInput0.getValue()).toBe('expressionTest1');

      expect(await harness.numRegexMatchSubforms()).toBe(1);
      const regexMatchSubform = (await harness.regexMatchSubforms())[0];
      const regexInput = await regexMatchSubform!.regexInput();
      expect(await regexInput.getValue()).toBe('test');
      const lengthInput = await regexMatchSubform!.lengthInput();
      expect(await lengthInput.getValue()).toBe('20000000');
      const regexModeSelect = await regexMatchSubform!.modeSelect();
      expect(await regexModeSelect.getValueText()).toBe('All Hits');

      expect(await harness.numLiteralMatchSubforms()).toBe(1);
      const literalMatchSubform = (await harness.literalMatchSubforms())[0];
      const literalInput = await literalMatchSubform!.literalInput();
      expect(await literalInput.getValue()).toBe('test');
      const literalModeSelect = await literalMatchSubform!.modeSelect();
      expect(await literalModeSelect.getValueText()).toBe('All Hits');

      expect(await harness.numModificationTimeSubforms()).toBe(1);
      const modificationTimeSubform = (
        await harness.modificationTimeSubforms()
      )[0];
      expect(await modificationTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );
      expect(await modificationTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );

      expect(await harness.numFileSizeSubforms()).toBe(1);
      const sizeSubform = (await harness.fileSizeSubforms())[0];
      const minFileSizeInput = await sizeSubform!.minFileSizeInput();
      const maxFileSizeInput = await sizeSubform!.maxFileSizeInput();
      expect(await minFileSizeInput.getValue()).toBe('10 kB');
      expect(await maxFileSizeInput.getValue()).toBe('20 MB');
    });
  });
});
