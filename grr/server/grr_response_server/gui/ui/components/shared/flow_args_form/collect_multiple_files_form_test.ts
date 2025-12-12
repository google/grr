import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  CollectMultipleFilesArgs,
  FileFinderContentsLiteralMatchConditionMode,
  FileFinderContentsRegexMatchConditionMode,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {CollectMultipleFilesForm} from './collect_multiple_files_form';
import {CollectMultipleFilesFormHarness} from './testing/collect_multiple_files_form_harness';

initTestEnvironment();

async function createComponent(flowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(CollectMultipleFilesForm);
  if (flowArgs) {
    fixture.componentRef.setInput('initialFlowArgs', flowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    CollectMultipleFilesFormHarness,
  );
  return {fixture, harness};
}

describe('Collect Multiple Files Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [CollectMultipleFilesForm, NoopAnimationsModule],
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
        expect(flowName).toBe('CollectMultipleFiles');
        expect(flowArgs).toEqual({
          pathExpressions: ['/some/path'],
          contentsLiteralMatch: {
            literal: btoa('test'),
            mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
          },
          contentsRegexMatch: {
            regex: btoa('test'),
            mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
            length: '30000000',
          },
          modificationTime: {
            minLastModifiedTime: '1704114000000000',
            maxLastModifiedTime: '1704115800000000',
          },
          accessTime: {
            minLastAccessTime: '1704117600000000',
            maxLastAccessTime: '1704119400000000',
          },
          inodeChangeTime: {
            minLastInodeChangeTime: '1704121200000000',
            maxLastInodeChangeTime: '1704123000000000',
          },
          size: {
            minFileSize: '10000000',
            maxFileSize: '20000000',
          },
          extFlags: {
            linuxBitsSet: 0,
            linuxBitsUnset: 0x00008000,
            osxBitsSet: 0x00000002,
            osxBitsUnset: 0,
          },
        });
        onSubmitCalled = true;
      },
    );
    const globExpressionInputs = await harness.globExpressionInputs();
    const globExpressionInput = await globExpressionInputs[0].input();
    await globExpressionInput.setValue('/some/path');

    const literalMatchFilterButton = await harness.literalMatchFilterButton();
    await literalMatchFilterButton.click();
    const literalMatchSubform = await harness.literalMatchSubform();
    const literalInput = await literalMatchSubform!.literalInput();
    await literalInput.setValue('test');
    const literalModeSelect = await literalMatchSubform!.modeSelect();
    await literalModeSelect.clickOptions({text: 'All Hits'});

    const regexMatchFilterButton = await harness.regexMatchFilterButton();
    await regexMatchFilterButton.click();
    const regexMatchSubform = await harness.regexMatchSubform();
    const regexInput = await regexMatchSubform!.regexInput();
    await regexInput.setValue('test');
    const regexModeSelect = await regexMatchSubform!.modeSelect();
    await regexModeSelect.clickOptions({text: 'All Hits'});
    const lengthInput = await regexMatchSubform!.lengthInput();
    await lengthInput.setValue('30000000');

    const modificationTimeFilterButton =
      await harness.modificationTimeFilterButton();
    await modificationTimeFilterButton.click();
    const modificationTimeSubform = await harness.modificationTimeSubform();
    const fromModificationTime = await modificationTimeSubform!.fromDateInput();
    await fromModificationTime.setValue('01/01/2024 1:00 PM UTC');
    const toModificationTime = await modificationTimeSubform!.toDateInput();
    await toModificationTime.setValue('01/01/2024 1:30 PM UTC');

    const accessTimeFilterButton = await harness.accessTimeFilterButton();
    await accessTimeFilterButton.click();
    const accessTimeSubform = await harness.accessTimeSubform();
    const fromAccessDateInput = await accessTimeSubform!.fromDateInput();
    await fromAccessDateInput.setValue('01/01/2024 2:00 PM UTC');
    const toAccessDateInput = await accessTimeSubform!.toDateInput();
    await toAccessDateInput.setValue('01/01/2024 2:30 PM UTC');

    const inodeChangeTimeFilterButton =
      await harness.inodeChangeTimeFilterButton();
    await inodeChangeTimeFilterButton.click();
    const inodeChangeTimeSubform = await harness.inodeChangeTimeSubform();
    const fromInodeChangeTime = await inodeChangeTimeSubform!.fromDateInput();
    await fromInodeChangeTime.setValue('01/01/2024 3:00 PM UTC');
    const toInodeChangeTime = await inodeChangeTimeSubform!.toDateInput();
    await toInodeChangeTime.setValue('01/01/2024 3:30 PM UTC');

    const fileSizeFilterButton = await harness.fileSizeFilterButton();
    await fileSizeFilterButton.click();
    const fileSizeSubform = await harness.fileSizeSubform();
    const fileSizeInput = await fileSizeSubform!.minFileSizeInput();
    await fileSizeInput.setValue('10000000 B');

    const extFlagsFilterButton = await harness.extFlagsFilterButton();
    await extFlagsFilterButton.click();
    const extFlagsSubform = await harness.extFlagsSubform();
    await extFlagsSubform!.selectIncludeFlag('uimmutable');
    await extFlagsSubform!.selectEitherFlag('archived');
    await extFlagsSubform!.selectExcludeFlag('t');

    const submitButton = await harness.getSubmitButton();

    await submitButton.submit();
    expect(onSubmitCalled).toBeTrue();
  });

  it('converts the form state to flow args', async () => {
    const {fixture} = await createComponent();
    const flowArgs = fixture.componentInstance.convertFormStateToFlowArgs({
      pathExpressions: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      contentsLiteralMatch: {
        literal: 'test',
        mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
      },
      contentsRegexMatch: {
        regex: 'test',
        mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
        length: 30000000,
      },
      modificationTime: {
        fromTime: new Date('2024-01-01T13:00:00Z'),
        toTime: new Date('2024-01-01T13:30:00Z'),
      },
      accessTime: {
        fromTime: new Date('2024-01-01T14:00:00Z'),
        toTime: new Date('2024-01-01T14:30:00Z'),
      },
      inodeChangeTime: {
        fromTime: new Date('2024-01-01T15:00:00Z'),
        toTime: new Date('2024-01-01T15:30:00Z'),
      },
      size: {
        minFileSize: 10000000,
        maxFileSize: 20000000,
      },
      extFlags: {
        linuxBitsSet: 0,
        linuxBitsUnset: 0x00008000,
        osxBitsSet: 0x00000002,
        osxBitsUnset: 0,
      },
    });
    const expectedFlowArgs: CollectMultipleFilesArgs = {
      pathExpressions: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      contentsLiteralMatch: {
        literal: btoa('test'),
        mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
      },
      contentsRegexMatch: {
        regex: btoa('test'),
        mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
        length: '30000000',
      },
      modificationTime: {
        minLastModifiedTime: '1704114000000000',
        maxLastModifiedTime: '1704115800000000',
      },
      accessTime: {
        minLastAccessTime: '1704117600000000',
        maxLastAccessTime: '1704119400000000',
      },
      inodeChangeTime: {
        minLastInodeChangeTime: '1704121200000000',
        maxLastInodeChangeTime: '1704123000000000',
      },
      size: {
        minFileSize: '10000000',
        maxFileSize: '20000000',
      },
      extFlags: {
        linuxBitsSet: 0,
        linuxBitsUnset: 0x00008000,
        osxBitsSet: 0x00000002,
        osxBitsUnset: 0,
      },
    };
    expect(flowArgs).toEqual(expectedFlowArgs);
  });

  it('converts the flow args to form state', async () => {
    const {fixture} = await createComponent();
    const flowArgs: CollectMultipleFilesArgs = {
      pathExpressions: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      contentsLiteralMatch: {
        literal: btoa('test'),
        mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
      },
      contentsRegexMatch: {
        regex: btoa('test'),
        mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
        length: '30000000',
      },
      modificationTime: {
        minLastModifiedTime: '1704114000000000',
        maxLastModifiedTime: '1704115800000000',
      },
      accessTime: {
        minLastAccessTime: '1704117600000000',
        maxLastAccessTime: '1704119400000000',
      },
      inodeChangeTime: {
        minLastInodeChangeTime: '1704121200000000',
        maxLastInodeChangeTime: '1704123000000000',
      },
      size: {
        minFileSize: '10000000',
        maxFileSize: '20000000',
      },
      extFlags: {
        linuxBitsSet: 0,
        linuxBitsUnset: 0x00008000,
        osxBitsSet: 0x00000002,
        osxBitsUnset: 0,
      },
    };
    const formState =
      fixture.componentInstance.convertFlowArgsToFormState(flowArgs);

    expect(formState).toEqual({
      pathExpressions: ['/some/path/with/trailing/spaces/tabs/and/linebreaks'],
      contentsLiteralMatch: {
        literal: 'test',
        mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
      },
      contentsRegexMatch: {
        regex: 'test',
        mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
        length: 30000000,
      },
      modificationTime: {
        fromTime: new Date('2024-01-01T13:00:00Z'),
        toTime: new Date('2024-01-01T13:30:00Z'),
      },
      accessTime: {
        fromTime: new Date('2024-01-01T14:00:00Z'),
        toTime: new Date('2024-01-01T14:30:00Z'),
      },
      inodeChangeTime: {
        fromTime: new Date('2024-01-01T15:00:00Z'),
        toTime: new Date('2024-01-01T15:30:00Z'),
      },
      size: {
        minFileSize: 10000000,
        maxFileSize: 20000000,
      },
      extFlags: {
        linuxBitsSet: 0,
        linuxBitsUnset: 0x00008000,
        osxBitsSet: 0x00000002,
        osxBitsUnset: 0,
      },
    });
  });

  it('hides the submit button when editable is false', async () => {
    const {harness} = await createComponent(undefined, false);
    expect(await harness.hasSubmitButton()).toBeFalse();
  });

  it('initializes one empty path expression and allsubforms as inactive', async () => {
    const {harness} = await createComponent();

    expect(await harness.globExpressionInputs()).toHaveSize(1);
    expect(await harness.filterConditions()).toHaveSize(7);

    const literalMatchFilterButton = await harness.literalMatchFilterButton();
    expect(
      await harness.isAddFilterButton(literalMatchFilterButton),
    ).toBeTrue();

    const regexMatchFilterButton = await harness.regexMatchFilterButton();
    expect(await harness.isAddFilterButton(regexMatchFilterButton)).toBeTrue();

    const modificationTimeFilterButton =
      await harness.modificationTimeFilterButton();
    expect(
      await harness.isAddFilterButton(modificationTimeFilterButton),
    ).toBeTrue();

    const accessTimeFilterButton = await harness.accessTimeFilterButton();
    expect(await harness.isAddFilterButton(accessTimeFilterButton)).toBeTrue();

    const inodeChangeTimeFilterButton =
      await harness.inodeChangeTimeFilterButton();
    expect(
      await harness.isAddFilterButton(inodeChangeTimeFilterButton),
    ).toBeTrue();

    const fileSizeFilterButton = await harness.fileSizeFilterButton();
    expect(await harness.isAddFilterButton(fileSizeFilterButton)).toBeTrue();

    const extFlagsFilterButton = await harness.extFlagsFilterButton();
    expect(await harness.isAddFilterButton(extFlagsFilterButton)).toBeTrue();
  });

  it('adds path expression', async () => {
    const {harness} = await createComponent();
    const globExpressionInputs = await harness.globExpressionInputs();
    expect(globExpressionInputs).toHaveSize(1);

    const addPathExpressionButton = await harness.addPathExpressionButton();
    await addPathExpressionButton.click();

    const newGlobExpressionInputs = await harness.globExpressionInputs();
    expect(newGlobExpressionInputs).toHaveSize(2);
  });

  it('removes path expression', async () => {
    const {harness} = await createComponent();

    const globExpressionInputs = await harness.globExpressionInputs();
    expect(globExpressionInputs).toHaveSize(1);

    await harness.removePathExpression(0);

    const newGlobExpressionInputs = await harness.globExpressionInputs();
    expect(newGlobExpressionInputs).toHaveSize(0);
  });

  it('adds literal match form', async () => {
    const {harness, fixture} = await createComponent();
    expect(await harness.hasLiteralMatchSubform()).toBeFalse();
    expect(
      fixture.componentInstance.controls.contentsLiteralMatch,
    ).not.toBeDefined();

    const literalMatchFilterButton = await harness.literalMatchFilterButton();
    await literalMatchFilterButton.click();

    expect(await harness.hasLiteralMatchSubform()).toBeTrue();
    expect(
      fixture.componentInstance.controls.contentsLiteralMatch,
    ).toBeDefined();
  });

  it('adds regex match form', async () => {
    const {harness, fixture} = await createComponent();

    expect(await harness.hasRegexMatchSubform()).toBeFalse();
    expect(
      fixture.componentInstance.controls.contentsRegexMatch,
    ).not.toBeDefined();

    const regexMatchFilterButton = await harness.regexMatchFilterButton();
    await regexMatchFilterButton.click();

    expect(await harness.hasRegexMatchSubform()).toBeTrue();
    expect(fixture.componentInstance.controls.contentsRegexMatch).toBeDefined();
  });

  it('adds modification time form', async () => {
    const {harness, fixture} = await createComponent();
    expect(await harness.hasModificationTimeSubform()).toBeFalse();
    expect(
      fixture.componentInstance.controls.modificationTime,
    ).not.toBeDefined();

    const modificationTimeFilterButton =
      await harness.modificationTimeFilterButton();
    await modificationTimeFilterButton.click();

    expect(await harness.hasModificationTimeSubform()).toBeTrue();
    expect(fixture.componentInstance.controls.modificationTime).toBeDefined();
  });

  it('adds access time form', async () => {
    const {harness, fixture} = await createComponent();

    expect(await harness.hasAccessTimeSubform()).toBeFalse();
    expect(fixture.componentInstance.controls.accessTime).not.toBeDefined();

    const accessTimeFilterButton = await harness.accessTimeFilterButton();
    await accessTimeFilterButton.click();

    expect(await harness.hasAccessTimeSubform()).toBeTrue();
    expect(fixture.componentInstance.controls.accessTime).toBeDefined();
  });

  it('adds inode change time form', async () => {
    const {harness, fixture} = await createComponent();
    expect(await harness.hasInodeChangeTimeSubform()).toBeFalse();
    expect(
      fixture.componentInstance.controls.inodeChangeTime,
    ).not.toBeDefined();

    const inodeChangeTimeFilterButton =
      await harness.inodeChangeTimeFilterButton();
    await inodeChangeTimeFilterButton.click();

    expect(await harness.hasInodeChangeTimeSubform()).toBeTrue();
    expect(fixture.componentInstance.controls.inodeChangeTime).toBeDefined();
  });

  it('adds file size form', async () => {
    const {harness, fixture} = await createComponent();
    expect(await harness.hasFileSizeSubform()).toBeFalse();
    expect(fixture.componentInstance.controls.size).not.toBeDefined();

    const fileSizeFilterButton = await harness.fileSizeFilterButton();
    await fileSizeFilterButton.click();

    expect(await harness.hasFileSizeSubform()).toBeTrue();
    expect(fixture.componentInstance.controls.size).toBeDefined();
  });

  it('adds extended flags form', async () => {
    const {harness, fixture} = await createComponent();
    expect(await harness.hasExtFlagsSubform()).toBeFalse();
    expect(fixture.componentInstance.controls.extFlags).not.toBeDefined();

    const extFlagsFilterButton = await harness.extFlagsFilterButton();
    await extFlagsFilterButton.click();

    expect(await harness.hasExtFlagsSubform()).toBeTrue();
    expect(fixture.componentInstance.controls.extFlags).toBeDefined();
  });

  describe('Initialization with fixed flow args', () => {
    it('initializes empty path expression', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        pathExpressions: [],
      };
      const {harness} = await createComponent(testFlowArgs);

      const globExpressionInputs = await harness.globExpressionInputs();
      expect(globExpressionInputs).toHaveSize(1);

      const globExpressionInput = await globExpressionInputs[0].input();
      expect(await globExpressionInput.getValue()).toBe('');
    });

    it('should initialize path expressions', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        pathExpressions: ['expressionTest1', 'expressionTest2'],
      };
      const {harness} = await createComponent(testFlowArgs);

      const globExpressionInputs = await harness.globExpressionInputs();
      expect(globExpressionInputs).toHaveSize(2);

      const globExpressionInput0 = await globExpressionInputs[0].input();
      const globExpressionInput1 = await globExpressionInputs[1].input();

      expect(await globExpressionInput0.getValue()).toBe('expressionTest1');
      expect(await globExpressionInput1.getValue()).toBe('expressionTest2');
    });

    it('should initialize one empty path expression when pathExpressions is undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        pathExpressions: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);

      const globExpressionInputs = await harness.globExpressionInputs();
      expect(globExpressionInputs).toHaveSize(1);

      const globExpressionInput = await globExpressionInputs[0].input();
      expect(await globExpressionInput.getValue()).toBe('');
    });

    it('initializes a regex match condition', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsRegexMatch: {
          regex: btoa('test'),
          mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
          length: '20000000',
        },
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.hasRegexMatchSubform()).toBeTrue();
      const regexMatchSubform = await harness.regexMatchSubform();
      const regexInput = await regexMatchSubform!.regexInput();
      expect(await regexInput.getValue()).toBe('test');
      const lengthInput = await regexMatchSubform!.lengthInput();
      expect(await lengthInput.getValue()).toBe('20000000');
      const regexModeSelect = await regexMatchSubform!.modeSelect();
      expect(await regexModeSelect.getValueText()).toBe('All Hits');
    });

    it('hides regex match condition when undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsRegexMatch: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasRegexMatchSubform()).toBeFalse();
    });

    it('initializes a literal match condition', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsLiteralMatch: {
          literal: btoa('test'),
          mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
        },
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.hasLiteralMatchSubform()).toBeTrue();
      const literalMatchSubform = await harness.literalMatchSubform();
      const literalInput = await literalMatchSubform!.literalInput();
      expect(await literalInput.getValue()).toBe('test');
      const literalModeSelect = await literalMatchSubform!.modeSelect();
      expect(await literalModeSelect.getValueText()).toBe('All Hits');
    });

    it('hides a literal match condition when undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsLiteralMatch: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasLiteralMatchSubform()).toBeFalse();
    });

    it('initializes a modification time condition', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        modificationTime: {
          minLastModifiedTime: '4242000000',
          maxLastModifiedTime: '4343000000',
        },
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.hasModificationTimeSubform()).toBeTrue();
      const modificationTimeSubform = await harness.modificationTimeSubform();

      expect(await modificationTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );

      expect(await modificationTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );
    });

    it('hides a modification time condition when undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        modificationTime: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasModificationTimeSubform()).toBeFalse();
    });

    it('should show an access time condition', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        accessTime: {
          minLastAccessTime: '4242000000',
          maxLastAccessTime: '4343000000',
        },
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.hasAccessTimeSubform()).toBeTrue();
      const accessTimeSubform = await harness.accessTimeSubform();

      expect(await accessTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );

      expect(await accessTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );
    });

    it('hides an access time condition when undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        accessTime: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasAccessTimeSubform()).toBeFalse();
    });

    it('should show an inode change time condition', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        inodeChangeTime: {
          minLastInodeChangeTime: '4242000000',
          maxLastInodeChangeTime: '4343000000',
        },
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.hasInodeChangeTimeSubform()).toBeTrue();
      const inodeChangeTimeSubform = await harness.inodeChangeTimeSubform();

      expect(await inodeChangeTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );

      expect(await inodeChangeTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );
    });

    it('hides inode change time condition when undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        inodeChangeTime: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasInodeChangeTimeSubform()).toBeFalse();
    });

    it('should show a file size condition', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        size: {
          minFileSize: '10000',
          maxFileSize: '20000000',
        },
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasFileSizeSubform()).toBeTrue();
      const sizeSubform = await harness.fileSizeSubform();
      const minFileSizeInput = await sizeSubform!.minFileSizeInput();
      const maxFileSizeInput = await sizeSubform!.maxFileSizeInput();

      expect(await minFileSizeInput.getValue()).toBe('10 kB');
      expect(await maxFileSizeInput.getValue()).toBe('20 MB');
    });

    it('hides file size condition when undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        size: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasFileSizeSubform()).toBeFalse();
    });

    it('should show ext flags condition', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        extFlags: {
          linuxBitsSet: 3, // 's' & 'u'
          linuxBitsUnset: 4, // 'c'
        },
      };
      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.hasExtFlagsSubform()).toBeTrue();
      const extFlagsSubform = await harness.extFlagsSubform();
      // No Os is set, so both Linux and Osx flags are shown.
      expect(await extFlagsSubform!.hasLinuxFlags()).toBeTrue();
      expect(await extFlagsSubform!.hasOsxFlags()).toBeTrue();

      expect(await extFlagsSubform!.getFlagSelection('s')).toBe('include');
      expect(await extFlagsSubform!.getFlagSelection('u')).toBe('include');
      expect(await extFlagsSubform!.getFlagSelection('c')).toBe('exclude');

      expect(await extFlagsSubform!.getFlagSelection('S')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('i')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('a')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('d')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('A')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('Z')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('B')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('X')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('E')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('I')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('j')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('t')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('D')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('T')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('h')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('e')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('C')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('nodump')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('uimmutable')).toBe(
        'either',
      );
      expect(await extFlagsSubform!.getFlagSelection('uappend')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('opaque')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('hidden')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('archived')).toBe(
        'either',
      );
      expect(await extFlagsSubform!.getFlagSelection('simmutable')).toBe(
        'either',
      );
      expect(await extFlagsSubform!.getFlagSelection('sappend')).toBe('either');
      expect(await extFlagsSubform!.getFlagSelection('sunlnk')).toBe('either');
    });

    it('hides ext file flag condition if undefined', async () => {
      const testFlowArgs: CollectMultipleFilesArgs = {
        extFlags: undefined,
      };
      const {harness} = await createComponent(testFlowArgs);
      expect(await harness.hasExtFlagsSubform()).toBeFalse();
    });

    it('can add multiple form elements', async () => {
      const linuxBitsSet = 3; // 1 & 2
      const linuxBitsUnset = 4; // 4
      const osxBitsSet = 1; // 1
      const osxBitsUnset = 2; // 2
      const testFlowArgs: CollectMultipleFilesArgs = {
        pathExpressions: ['expressionTest1'],
        contentsRegexMatch: {
          regex: btoa('test'),
          mode: FileFinderContentsRegexMatchConditionMode.FIRST_HIT,
          length: '20000000',
        },
        contentsLiteralMatch: {
          literal: btoa('test'),
          mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
        },
        modificationTime: {
          minLastModifiedTime: '4242000000',
          maxLastModifiedTime: '4343000000',
        },
        accessTime: {
          minLastAccessTime: '4242000000',
          maxLastAccessTime: '4343000000',
        },
        inodeChangeTime: {
          minLastInodeChangeTime: '4242000000',
          maxLastInodeChangeTime: '4343000000',
        },
        size: {
          minFileSize: '10000',
          maxFileSize: '20000000',
        },
        extFlags: {
          linuxBitsSet,
          linuxBitsUnset,
          osxBitsSet,
          osxBitsUnset,
        },
      };

      const {harness} = await createComponent(testFlowArgs);

      expect(await harness.globExpressionInputs()).toHaveSize(1);
      const globExpressionInputs = await harness.globExpressionInputs();
      const globExpressionInput0 = await globExpressionInputs[0].input();
      expect(await globExpressionInput0.getValue()).toBe('expressionTest1');

      expect(await harness.hasRegexMatchSubform()).toBeTrue();
      const regexMatchSubform = await harness.regexMatchSubform();
      const regexInput = await regexMatchSubform!.regexInput();
      expect(await regexInput.getValue()).toBe('test');
      const lengthInput = await regexMatchSubform!.lengthInput();
      expect(await lengthInput.getValue()).toBe('20000000');
      const regexModeSelect = await regexMatchSubform!.modeSelect();
      expect(await regexModeSelect.getValueText()).toBe('First Hit');

      expect(await harness.hasLiteralMatchSubform()).toBeTrue();
      const literalMatchSubform = await harness.literalMatchSubform();
      const literalInput = await literalMatchSubform!.literalInput();
      expect(await literalInput.getValue()).toBe('test');
      const literalModeSelect = await literalMatchSubform!.modeSelect();
      expect(await literalModeSelect.getValueText()).toBe('All Hits');

      expect(await harness.hasModificationTimeSubform()).toBeTrue();
      const modificationTimeSubform = await harness.modificationTimeSubform();
      expect(await modificationTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );
      expect(await modificationTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );

      expect(await harness.hasAccessTimeSubform()).toBeTrue();
      const accessTimeSubform = await harness.accessTimeSubform();
      expect(await accessTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );
      expect(await accessTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );

      expect(await harness.hasInodeChangeTimeSubform()).toBeTrue();
      const inodeChangeTimeSubform = await harness.inodeChangeTimeSubform();
      expect(await inodeChangeTimeSubform!.getFromUTCString()).toContain(
        'Thu, 01 Jan 1970 01:10:42 GMT',
      );
      expect(await inodeChangeTimeSubform!.getToUTCString()).toContain(
        'Thu, 01 Jan 1970 01:12:23 GMT',
      );

      expect(await harness.hasFileSizeSubform()).toBeTrue();
      const sizeSubform = await harness.fileSizeSubform();
      const minFileSizeInput = await sizeSubform!.minFileSizeInput();
      const maxFileSizeInput = await sizeSubform!.maxFileSizeInput();
      expect(await minFileSizeInput.getValue()).toBe('10 kB');
      expect(await maxFileSizeInput.getValue()).toBe('20 MB');

      expect(await harness.hasExtFlagsSubform()).toBeTrue();
      const extFlagsSubform = await harness.extFlagsSubform();

      expect(await extFlagsSubform!.hasLinuxFlags()).toBeTrue();
      expect(await extFlagsSubform!.hasOsxFlags()).toBeTrue();
    });
  });
});
