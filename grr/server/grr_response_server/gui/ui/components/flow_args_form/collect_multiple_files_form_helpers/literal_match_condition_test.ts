import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ControlContainer} from '@angular/forms';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  FileFinderContentsLiteralMatchCondition,
  FileFinderContentsLiteralMatchConditionMode,
} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';

import {
  createLiteralMatchFormGroup,
  fileFinderContentsLiteralMatchConditionToFormValue,
  formValuesToFileFinderContentsLiteralMatchCondition,
  LiteralMatchCondition,
} from './literal_match_condition';
import {HelpersModule} from './module';

initTestEnvironment();

describe('LiteralMatchCondition component', () => {
  let control: ReturnType<typeof createLiteralMatchFormGroup>;

  beforeEach(waitForAsync(() => {
    control = createLiteralMatchFormGroup();

    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, HelpersModule],
      providers: [
        {
          provide: ControlContainer,
          useValue: {
            control,
          },
        },
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('displays empty literal field and correctly filled mode field when initialized', () => {
    const fixture = TestBed.createComponent(LiteralMatchCondition);
    fixture.detectChanges();

    const literalField = fixture.debugElement.query(By.css('input'));
    const modeField = fixture.debugElement.query(By.css('mat-select'));
    expect(literalField.nativeElement.textContent).toBe('');
    expect(modeField.componentInstance.value).toBe(
      FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
    );
  });

  it('correctly exposes form value', async () => {
    const fixture = TestBed.createComponent(LiteralMatchCondition);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();

    const literalFieldHarness = await loader.getHarness(MatInputHarness);
    await literalFieldHarness.setValue('test');
    const modeFieldHarness = await loader.getHarness(MatSelectHarness);
    await modeFieldHarness.clickOptions({text: 'All Hits'});

    const expected: FileFinderContentsLiteralMatchCondition = {
      literal: 'test',
      mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
    };
    expect(control.value).toEqual(expected);
  });
});

describe('formValuesToFileFinderContentsLiteralMatchCondition()', () => {
  it('correctly converts form value to FileFinderContentsLiteralMatchCondition', () => {
    const source = {
      literal: 'test',
      mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
    };
    expect(formValuesToFileFinderContentsLiteralMatchCondition(source)).toEqual(
      {
        literal: btoa('test'),
        mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
      },
    );
  });
});

describe('fileFinderContentsLiteralMatchConditionToFormValue()', () => {
  it('correctly converts FileFinderContentsLiteralMatchCondition to form value', () => {
    const source = {
      literal: 'test',
      mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
    };
    expect(fileFinderContentsLiteralMatchConditionToFormValue(source)).toEqual({
      literal: atob('test'),
      mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
    });
  });

  it('correctly converts FileFinderContentsLiteralMatchCondition to form value (empty string)', () => {
    const source = {
      literal: '',
      mode: FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
    };
    expect(fileFinderContentsLiteralMatchConditionToFormValue(source)).toEqual({
      literal: '',
      mode: FileFinderContentsLiteralMatchConditionMode.FIRST_HIT,
    });
  });

  it('correctly converts FileFinderContentsLiteralMatchCondition to form value (undefined)', () => {
    const source = {
      literal: undefined,
      mode: undefined,
    };
    expect(fileFinderContentsLiteralMatchConditionToFormValue(source)).toEqual({
      literal: '',
      mode: undefined,
    });
  });
});
