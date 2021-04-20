import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ControlContainer, FormGroup} from '@angular/forms';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FileFinderContentsMatchConditionMode, FileFinderContentsRegexMatchCondition} from '@app/lib/api/api_interfaces';
import {initTestEnvironment} from '@app/testing';

import {HelpersModule} from './module';

import {createRegexMatchFormGroup, formValuesToFileFinderContentsRegexMatchCondition, RegexMatchCondition, RegexMatchRawFormValues} from './regex_match_condition';

initTestEnvironment();

describe('RegexMatchCondition component', () => {
  let control: FormGroup;

  beforeEach(waitForAsync(() => {
    control = createRegexMatchFormGroup();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HelpersModule,
          ],

          providers: [
            {
              provide: ControlContainer,
              useValue: {
                control,
              }
            },
          ],
        })
        .compileComponents();
  }));

  it('displays empty regex field and correctly filled mode and length fields when initialized',
     () => {
       const fixture = TestBed.createComponent(RegexMatchCondition);
       fixture.detectChanges();

       const regexField = fixture.debugElement.query(By.css('input'));
       const modeField = fixture.debugElement.query(By.css('mat-select'));
       const lengthField =
           fixture.debugElement.query(By.css('input[type=number]'));
       expect(regexField.nativeElement.textContent).toBe('');
       expect(modeField.componentInstance.value)
           .toBe(FileFinderContentsMatchConditionMode.FIRST_HIT);
       expect(lengthField.nativeElement.value).toBe('20000000');
     });

  it('correctly exposes form values', async () => {
    const fixture = TestBed.createComponent(RegexMatchCondition);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();

    const regexFieldHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[formControlName="regex"]'}));
    await regexFieldHarness.setValue('test');
    const modeFieldHarness = await loader.getHarness(MatSelectHarness);
    await modeFieldHarness.clickOptions({text: 'All Hits'});
    const lengthFieldHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[formControlName="length"]'}));
    await lengthFieldHarness.setValue('30000000');

    const expected: FileFinderContentsRegexMatchCondition = {
      regex: 'test',
      mode: FileFinderContentsMatchConditionMode.ALL_HITS,
      length: 30000000,
    };
    expect(control.value).toEqual(expected);
  });
});

describe('formValuesToFileFinderContentsRegexMatchCondition()', () => {
  it('correctly converts form value with decimal length', () => {
    const source: RegexMatchRawFormValues = {
      regex: 'test',
      mode: FileFinderContentsMatchConditionMode.ALL_HITS,
      length: 20000000.999,
    };
    const expected: FileFinderContentsRegexMatchCondition = {
      regex: 'test',
      mode: FileFinderContentsMatchConditionMode.ALL_HITS,
      length: 20000000,
    };
    expect(formValuesToFileFinderContentsRegexMatchCondition(source))
        .toEqual(expected);
  });
});
