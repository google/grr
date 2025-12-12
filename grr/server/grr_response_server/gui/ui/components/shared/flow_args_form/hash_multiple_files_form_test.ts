import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  FileFinderContentsLiteralMatchConditionMode,
  FileFinderContentsRegexMatchConditionMode,
  HashMultipleFilesArgs,
} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {HashMultipleFilesForm} from './hash_multiple_files_form';
import {HashMultipleFilesFormHarness} from './testing/hash_multiple_files_form_harness';

initTestEnvironment();

async function createComponent(fixedFlowArgs?: object, editable = true) {
  const fixture = TestBed.createComponent(HashMultipleFilesForm);
  if (fixedFlowArgs) {
    fixture.componentRef.setInput('fixedFlowArgs', fixedFlowArgs);
  }
  fixture.componentRef.setInput('editable', editable);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    HashMultipleFilesFormHarness,
  );
  return {fixture, harness};
}

describe('Hash Multiple Files Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HashMultipleFilesForm, NoopAnimationsModule],
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
        expect(flowName).toBe('HashMultipleFiles');
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
    const expectedFlowArgs: HashMultipleFilesArgs = {
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
    const flowArgs: HashMultipleFilesArgs = {
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
});
