import {
  fakeAsync,
  flush,
  TestBed,
  tick,
  waitForAsync,
} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FlowArgsFormModule} from '../../components/flow_args_form/module';
import {
  CollectMultipleFilesArgs,
  FileFinderContentsLiteralMatchConditionMode,
  FileFinderContentsRegexMatchConditionMode,
} from '../../lib/api/api_interfaces';
import {HttpApiService} from '../../lib/api/http_api_service';
import {mockHttpApiService} from '../../lib/api/http_api_service_test_util';
import {initTestEnvironment} from '../../testing';

import {CollectMultipleFilesForm} from './collect_multiple_files_form';

initTestEnvironment();

describe('CollectMultipleFilesForm', () => {
  beforeEach(waitForAsync(() => {
    return TestBed.configureTestingModule({
      imports: [ReactiveFormsModule, FlowArgsFormModule, NoopAnimationsModule],
      providers: [
        HttpApiService,
        {provide: HttpApiService, useFactory: mockHttpApiService},
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('start state', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    const pathsInputs = fixture.debugElement.queryAll(
      By.css('app-glob-expression-input'),
    );
    expect(pathsInputs.length).toBe(1);

    const conditionGroups = fixture.debugElement.queryAll(
      By.css('.conditions'),
    );
    expect(conditionGroups.length).toBe(2);

    expect(conditionGroups[0].nativeElement.textContent).toContain(
      'Filter by file content',
    );
    const fileContentFilters = conditionGroups[0].queryAll(By.css('button'));
    expect(fileContentFilters.length).toBe(2);
    expect(fileContentFilters[0].nativeElement.textContent).toContain(
      'Literal',
    );
    expect(fileContentFilters[1].nativeElement.textContent).toContain('Regex');

    expect(conditionGroups[1].nativeElement.textContent).toContain(
      'Filter by file attributes',
    );
    const fileAttributeFilters = conditionGroups[1].queryAll(By.css('button'));
    expect(fileAttributeFilters.length).toBe(5);
    expect(fileAttributeFilters[0].nativeElement.textContent).toContain(
      'Modification',
    );
    expect(fileAttributeFilters[1].nativeElement.textContent).toContain(
      'Access',
    );
    expect(fileAttributeFilters[2].nativeElement.textContent).toContain(
      'Inode',
    );
    expect(fileAttributeFilters[3].nativeElement.textContent).toContain('size');
    expect(fileAttributeFilters[4].nativeElement.textContent).toContain(
      'flags',
    );
  });

  it('adds path expression', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    let pathsInputs = fixture.debugElement.queryAll(
      By.css('app-glob-expression-input'),
    );
    expect(pathsInputs.length).toBe(1);

    const addPathExpression = fixture.debugElement.query(
      By.css('#button-add-path-expression'),
    );
    addPathExpression.nativeElement.click();
    fixture.detectChanges();

    pathsInputs = fixture.debugElement.queryAll(
      By.css('app-glob-expression-input'),
    );
    expect(pathsInputs.length).toBe(2);
  });

  it('removes path expression', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    let pathsInputs = fixture.debugElement.queryAll(
      By.css('app-glob-expression-input'),
    );
    expect(pathsInputs.length).toBe(1);

    const removePath = fixture.debugElement.query(By.css('#removePath0'));
    removePath.nativeElement.click();
    fixture.detectChanges();

    pathsInputs = fixture.debugElement.queryAll(
      By.css('app-glob-expression-input'),
    );
    expect(pathsInputs.length).toBe(0);
  });

  it('adds literal match form', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('input[name=literal]')),
    ).toBeFalsy();
    expect(
      fixture.debugElement.query(By.css('mat-select[name=literalMode]')),
    ).toBeFalsy();

    const literalMatchButton = fixture.debugElement.query(
      By.css('[name=literalMatch]'),
    );
    literalMatchButton.nativeElement.click();
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('input[name=literal]')),
    ).toBeTruthy();
    expect(
      fixture.debugElement.query(By.css('mat-select[name=literalMode]')),
    ).toBeTruthy();
  });

  it('adds regex match form', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('input[name=regex]'))).toBeFalsy();
    expect(
      fixture.debugElement.query(By.css('mat-select[name=mode]')),
    ).toBeFalsy();
    expect(
      fixture.debugElement.query(By.css('input[name=length]')),
    ).toBeFalsy();

    const regexMatchButton = fixture.debugElement.query(
      By.css('[name=regexMatch]'),
    );
    regexMatchButton.nativeElement.click();
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('input[name=regex]')),
    ).toBeTruthy();
    expect(
      fixture.debugElement.query(By.css('mat-select[name=mode]')),
    ).toBeTruthy();
    expect(
      fixture.debugElement.query(By.css('input[name=length]')),
    ).toBeTruthy();
  });

  it('adds modification time form', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('date-time-input[name=minTime]')),
    ).toBeFalsy();
    expect(
      fixture.debugElement.query(By.css('date-time-input[name=maxTime]')),
    ).toBeFalsy();

    const modificationTimeButton = fixture.debugElement.query(
      By.css('[name=modificationTime]'),
    );
    modificationTimeButton.nativeElement.click();
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('date-time-input[name=minTime]')),
    ).toBeTruthy();
    expect(
      fixture.debugElement.query(By.css('date-time-input[name=maxTime]')),
    ).toBeTruthy();
  });

  it('adds access time form', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('date-time-input[name=minTime]')),
    ).toBeFalsy();
    expect(
      fixture.debugElement.query(By.css('date-time-input[name=maxTime]')),
    ).toBeFalsy();

    const accessTimeButton = fixture.debugElement.query(
      By.css('[name=accessTime]'),
    );
    accessTimeButton.nativeElement.click();
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('date-time-input[name=minTime]')),
    ).toBeTruthy();
    expect(
      fixture.debugElement.query(By.css('date-time-input[name=maxTime]')),
    ).toBeTruthy();
  });

  it('adds inode change time form', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('date-time-input[name=minTime]')),
    ).toBeFalsy();
    expect(
      fixture.debugElement.query(By.css('date-time-input[name=maxTime]')),
    ).toBeFalsy();

    const inodeChangeTimeButton = fixture.debugElement.query(
      By.css('[name=inodeChangeTime]'),
    );
    inodeChangeTimeButton.nativeElement.click();
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('date-time-input[name=minTime]')),
    ).toBeTruthy();
    expect(
      fixture.debugElement.query(By.css('date-time-input[name=maxTime]')),
    ).toBeTruthy();
  });

  it('adds file size form', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('input[name=minFileSize]')),
    ).toBeFalsy();
    expect(
      fixture.debugElement.query(By.css('input[name=maxFileSize]')),
    ).toBeFalsy();

    const fileSizeButton = fixture.debugElement.query(By.css('[name=size]'));
    fileSizeButton.nativeElement.click();
    fixture.detectChanges();

    expect(
      fixture.debugElement.query(By.css('input[name=minFileSize]')),
    ).toBeTruthy();
    expect(
      fixture.debugElement.query(By.css('input[name=maxFileSize]')),
    ).toBeTruthy();
  });

  it('adds extended flags form', () => {
    const fixture = TestBed.createComponent(CollectMultipleFilesForm);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).not.toContain('Linux file flags');
    expect(fixture.nativeElement.textContent).not.toContain('macOS file flags');

    const extFileFlagsButton = fixture.debugElement.query(
      By.css('[name=extFlags]'),
    );
    extFileFlagsButton.nativeElement.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Linux file flags');
    expect(fixture.nativeElement.textContent).toContain('macOS file flags');
  });

  describe('resetFlowArgs', () => {
    it('should add 2 path expressions', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        pathExpressions: ['expressionTest1', 'expressionTest2'],
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const pathExpressions = fixture.debugElement.queryAll(
        By.css('app-glob-expression-input'),
      );
      expect(pathExpressions.length).toBe(2);

      const pathExpressionInputs = fixture.debugElement.queryAll(
        By.css('app-glob-expression-input input'),
      );
      expect(pathExpressionInputs[0].nativeElement.value).toBe(
        'expressionTest1',
      );
      expect(pathExpressionInputs[1].nativeElement.value).toBe(
        'expressionTest2',
      );

      /* We need to flush due to getting the following error otherwise:

          `Error: 1 timer(s) still in the queue`

          This happens due to MatFormFieldFloatingLabel running the
          following:

          `setTimeout(() => this._parent._handleLabelResized());`

          When GlobExpressionInput component gets rendered, as we autofocus the
          HTML Input element through FlowArgumentForm Component.
         */
      flush();
    }));

    it('should not add any path expression', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        pathExpressions: [],
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const pathExpressions = fixture.debugElement.queryAll(
        By.css('app-glob-expression-input input'),
      );
      expect(pathExpressions.length).toBe(1);

      const pathExpressionInput = fixture.debugElement.query(
        By.css('app-glob-expression-input input'),
      );
      expect(pathExpressionInput.nativeElement.value).toBe('');
    });

    it('should not add any path expression', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        pathExpressions: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const pathExpression = fixture.debugElement.query(
        By.css('app-glob-expression-input input'),
      );

      expect(pathExpression.nativeElement.value).toBe('');
    });

    it('should show a regex match condition', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsRegexMatch: {
          regex: btoa('test'),
          mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
          length: '20000000',
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const regexInput = fixture.debugElement.query(
        By.css('regex-match-condition [name=regex]'),
      );
      expect(regexInput.nativeElement.value).toBe('test');

      const lengthInput = fixture.debugElement.query(
        By.css('regex-match-condition [name=length]'),
      );
      expect(lengthInput.nativeElement.value).toBe('20000000');

      const regexModeInput = fixture.debugElement.query(
        By.css('regex-match-condition [name=mode]'),
      );
      expect(regexModeInput.nativeElement.innerText).toBe('All Hits');

      /* We need to flush due to getting the following error otherwise:

         `Error: 1 timer(s) still in the queue`

          This happens due to MatFormFieldFloatingLabel running the
          following:

          `setTimeout(() => this._parent._handleLabelResized());`

          When RegexMatchCondition component gets rendered, as we autofocus the
          HTML Input element through FlowArgumentForm Component.
         */
      flush();
    }));

    it('should not show a regex match condition', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsRegexMatch: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const regexMatchConditions = fixture.debugElement.queryAll(
        By.css('regex-match-condition'),
      );

      expect(regexMatchConditions.length).toBe(0);
    });

    it('should show a literal match condition', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsLiteralMatch: {
          literal: btoa('test'),
          mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.changeDetectorRef.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const literalBlocks = fixture.debugElement.queryAll(
        By.css('literal-match-condition'),
      );
      expect(literalBlocks.length).toBe(1);

      const literalInput = fixture.debugElement.query(
        By.css('literal-match-condition [name=literal]'),
      );
      expect(literalInput.nativeElement.value).toBe('test');

      const modeInput = fixture.debugElement.query(
        By.css('literal-match-condition [name=literalMode]'),
      );
      expect(modeInput.nativeElement.innerText).toBe('All Hits');

      /* We need to flush due to getting the following error otherwise:

          `Error: 1 timer(s) still in the queue`

          This happens due to MatFormFieldFloatingLabel running the
          following:

          `setTimeout(() => this._parent._handleLabelResized());`

          When LiteralMatchCondition component gets rendered, as we autofocus
          the HTML Input element through FlowArgumentForm Component.

          */
      flush();
    }));

    it('should not show a literal match condition', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        contentsLiteralMatch: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const literalInputs = fixture.debugElement.queryAll(
        By.css('literal-match-condition [name=literal]'),
      );

      expect(literalInputs.length).toBe(0);
    });

    it('should show a modification time condition', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        modificationTime: {
          minLastModifiedTime: '4242000000',
          maxLastModifiedTime: '4343000000',
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const modificationTimeBlocks = fixture.debugElement.queryAll(
        By.css('time-range-condition[title=modification]'),
      );

      expect(modificationTimeBlocks.length).toBe(1);

      const minModificationTime = fixture.debugElement.query(
        By.css('time-range-condition[title=modification] [name=minTime] input'),
      );
      expect(minModificationTime.nativeElement.value).toBe(
        '1970-01-01 01:10:42',
      );

      const maxModificationTime = fixture.debugElement.query(
        By.css('time-range-condition[title=modification] [name=maxTime] input'),
      );
      expect(maxModificationTime.nativeElement.value).toBe(
        '1970-01-01 01:12:23',
      );
    }));

    it('should not show a modification time condition', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        modificationTime: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const modificationTimeBlocks = fixture.debugElement.queryAll(
        By.css('time-range-condition[title=modification]'),
      );

      expect(modificationTimeBlocks.length).toBe(0);
    });

    it('should show an access time condition', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        accessTime: {
          minLastAccessTime: '4242000000',
          maxLastAccessTime: '4343000000',
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const accessTimeBlocks = fixture.debugElement.queryAll(
        By.css('time-range-condition[title=access]'),
      );

      expect(accessTimeBlocks.length).toBe(1);

      const minAccessTime = fixture.debugElement.query(
        By.css('time-range-condition[title=access] [name=minTime] input'),
      );
      expect(minAccessTime.nativeElement.value).toBe('1970-01-01 01:10:42');

      const maxAccessTime = fixture.debugElement.query(
        By.css('time-range-condition[title=access] [name=maxTime] input'),
      );
      expect(maxAccessTime.nativeElement.value).toBe('1970-01-01 01:12:23');
    }));

    it('should not show an access time condition', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        accessTime: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const accessTimeBlocks = fixture.debugElement.queryAll(
        By.css('time-range-condition[title=access]'),
      );

      expect(accessTimeBlocks.length).toBe(0);
    });

    it('should show an inode change time condition', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        inodeChangeTime: {
          minLastInodeChangeTime: '4242000000',
          maxLastInodeChangeTime: '4343000000',
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const inodeChangeTimeBlocks = fixture.debugElement.queryAll(
        By.css('time-range-condition[title="inode change"]'),
      );

      expect(inodeChangeTimeBlocks.length).toBe(1);

      const minInodeChangeTime = fixture.debugElement.query(
        By.css(
          'time-range-condition[title="inode change"] [name=minTime] input',
        ),
      );
      expect(minInodeChangeTime.nativeElement.value).toBe(
        '1970-01-01 01:10:42',
      );

      const maxInodeChangeTime = fixture.debugElement.query(
        By.css(
          'time-range-condition[title="inode change"] [name=maxTime] input',
        ),
      );
      expect(maxInodeChangeTime.nativeElement.value).toBe(
        '1970-01-01 01:12:23',
      );
    }));

    it('should not show an inode change time condition', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        inodeChangeTime: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const inodeChangeTimeBlocks = fixture.debugElement.queryAll(
        By.css('time-range-condition[title="inode change"]'),
      );

      expect(inodeChangeTimeBlocks.length).toBe(0);
    });

    it('should show a file size condition', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        size: {
          minFileSize: '10000',
          maxFileSize: '20000000',
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const size = fixture.debugElement.queryAll(By.css('size-condition'));

      expect(size.length).toBe(1);

      const minFileSize = fixture.debugElement.query(
        By.css('size-condition input[name=minFileSize]'),
      );
      expect(minFileSize.nativeElement.value).toBe('10 kB');

      const maxFileSize = fixture.debugElement.query(
        By.css('size-condition input[name=maxFileSize]'),
      );
      expect(maxFileSize.nativeElement.value).toBe('20 MB');
    }));

    it('should not show a file size condition', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        size: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const fileSizeBlocks = fixture.debugElement.queryAll(
        By.css('size-condition'),
      );

      expect(fileSizeBlocks.length).toBe(0);
    });

    it('should show the correct status for the Linux flags', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const linuxBitsSet = 3; // 1 & 2
      const checkedFlagIndexes = [0, 1];
      const linuxBitsUnset = 4; // 4
      const blockedFlagIndexes = [8];

      const testFlowArgs: CollectMultipleFilesArgs = {
        extFlags: {
          linuxBitsSet,
          linuxBitsUnset,
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const extFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition'),
      );

      expect(extFlagsBlocks.length).toBe(1);

      const extLinuxFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="linuxFileFlags"]'),
      );

      expect(extLinuxFlagsBlocks.length).toBe(1);

      const linuxFlags = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="linuxFileFlags"] mat-icon'),
      );

      for (const index of checkedFlagIndexes) {
        expect(linuxFlags[index].nativeElement.innerText).toBe('check');
      }

      for (const index of blockedFlagIndexes) {
        expect(linuxFlags[index].nativeElement.innerText).toBe('block');
      }
    }));

    it('should show the correct status for the macOS flags', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const osxBitsSet = 24; // 8 & 16
      const checkedFlagIndexes = [3];
      const osxBitsUnset = 7; // 1 & 2 & 4
      const blockedFlagIndexes = [0, 1, 2];

      const testFlowArgs: CollectMultipleFilesArgs = {
        extFlags: {
          osxBitsSet,
          osxBitsUnset,
        },
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const extFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition'),
      );

      expect(extFlagsBlocks.length).toBe(1);

      const extOSXFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="osxFileFlags"]'),
      );

      expect(extOSXFlagsBlocks.length).toBe(1);

      const osxFlags = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="osxFileFlags"] mat-icon'),
      );

      for (const index of checkedFlagIndexes) {
        expect(osxFlags[index].nativeElement.innerText).toBe('check');
      }

      for (const index of blockedFlagIndexes) {
        expect(osxFlags[index].nativeElement.innerText).toBe('block');
      }
    }));

    it('should not show an OS file flag condition', () => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const testFlowArgs: CollectMultipleFilesArgs = {
        extFlags: undefined,
      };

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      fixture.detectChanges();

      const extFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition'),
      );

      expect(extFlagsBlocks.length).toBe(0);
    });

    it('should add multiple form elements', fakeAsync(() => {
      const fixture = TestBed.createComponent(CollectMultipleFilesForm);
      fixture.detectChanges();

      const linuxBitsSet = 3; // 1 & 2
      const checkedLinuxFlagIndexes = [0, 1];
      const linuxBitsUnset = 4; // 4
      const blockedLinuxFlagIndexes = [8];
      const osxBitsSet = 1; // 1
      const checkedOSXFlagIndexes = [0];
      const osxBitsUnset = 2; // 2
      const blockedOSXFlagIndexes = [1];

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

      fixture.componentInstance.resetFlowArgs(testFlowArgs);

      // Child form components get rendered
      fixture.detectChanges();

      tick();

      // Child form components are populated with the patched values
      fixture.detectChanges();

      const pathExpression = fixture.debugElement.query(
        By.css('app-glob-expression-input input'),
      );
      expect(pathExpression.nativeElement.value).toBe('expressionTest1');

      const regexInput = fixture.debugElement.query(
        By.css('regex-match-condition [name=regex]'),
      );
      expect(regexInput.nativeElement.value).toBe('test');

      const lengthInput = fixture.debugElement.query(
        By.css('regex-match-condition [name=length]'),
      );
      expect(lengthInput.nativeElement.value).toBe('20000000');

      const regexModeInput = fixture.debugElement.query(
        By.css('regex-match-condition [name=mode]'),
      );
      expect(regexModeInput.nativeElement.innerText).toBe('First Hit');

      const literalInput = fixture.debugElement.query(
        By.css('literal-match-condition [name=literal]'),
      );
      expect(literalInput.nativeElement.value).toBe('test');

      const literalModeInput = fixture.debugElement.query(
        By.css('literal-match-condition [name=literalMode]'),
      );
      expect(literalModeInput.nativeElement.innerText).toBe('All Hits');

      const minModificationTime = fixture.debugElement.query(
        By.css('time-range-condition[title=modification] [name=minTime] input'),
      );
      expect(minModificationTime.nativeElement.value).toBe(
        '1970-01-01 01:10:42',
      );

      const maxModificationTime = fixture.debugElement.query(
        By.css('time-range-condition[title=modification] [name=maxTime] input'),
      );
      expect(maxModificationTime.nativeElement.value).toBe(
        '1970-01-01 01:12:23',
      );

      const minAccessTime = fixture.debugElement.query(
        By.css('time-range-condition[title=access] [name=minTime] input'),
      );
      expect(minAccessTime.nativeElement.value).toBe('1970-01-01 01:10:42');

      const maxAccessTime = fixture.debugElement.query(
        By.css('time-range-condition[title=access] [name=maxTime] input'),
      );
      expect(maxAccessTime.nativeElement.value).toBe('1970-01-01 01:12:23');

      const minInodeChangeTime = fixture.debugElement.query(
        By.css(
          'time-range-condition[title="inode change"] [name=minTime] input',
        ),
      );
      expect(minInodeChangeTime.nativeElement.value).toBe(
        '1970-01-01 01:10:42',
      );

      const maxInodeChangeTime = fixture.debugElement.query(
        By.css(
          'time-range-condition[title="inode change"] [name=maxTime] input',
        ),
      );
      expect(maxInodeChangeTime.nativeElement.value).toBe(
        '1970-01-01 01:12:23',
      );
      const minFileSize = fixture.debugElement.query(
        By.css('size-condition input[name=minFileSize]'),
      );
      expect(minFileSize.nativeElement.value).toBe('10 kB');

      const maxFileSize = fixture.debugElement.query(
        By.css('size-condition input[name=maxFileSize]'),
      );
      expect(maxFileSize.nativeElement.value).toBe('20 MB');

      const extFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition'),
      );

      expect(extFlagsBlocks.length).toBe(1);

      // Linux Ext. Flags
      const extLinuxFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="linuxFileFlags"]'),
      );

      expect(extLinuxFlagsBlocks.length).toBe(1);

      const linuxFlags = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="linuxFileFlags"] mat-icon'),
      );

      for (const index of checkedLinuxFlagIndexes) {
        expect(linuxFlags[index].nativeElement.innerText).toBe('check');
      }

      for (const index of blockedLinuxFlagIndexes) {
        expect(linuxFlags[index].nativeElement.innerText).toBe('block');
      }

      // OSX Ext. Flags
      const extOSXFlagsBlocks = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="osxFileFlags"]'),
      );

      expect(extOSXFlagsBlocks.length).toBe(1);

      const osxFlags = fixture.debugElement.queryAll(
        By.css('ext-flags-condition [name="osxFileFlags"] mat-icon'),
      );

      for (const index of checkedOSXFlagIndexes) {
        expect(osxFlags[index].nativeElement.innerText).toBe('check');
      }

      for (const index of blockedOSXFlagIndexes) {
        expect(osxFlags[index].nativeElement.innerText).toBe('block');
      }

      /* We need to flush due to getting the following error otherwise:

          `Error: 1 timer(s) still in the queue`

          This happens due to MatFormFieldFloatingLabel running the
          following:

          `setTimeout(() => this._parent._handleLabelResized());`

          When ExtFlagsCondition component get rendered, as we autofocus
          the HTML Input element through FlowArgumentForm Component.
          */
      flush();
    }));
  });
});
