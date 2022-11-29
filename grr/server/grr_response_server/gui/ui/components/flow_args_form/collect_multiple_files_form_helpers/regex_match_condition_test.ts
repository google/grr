import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {ControlContainer} from '@angular/forms';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileFinderContentsRegexMatchConditionMode} from '../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../testing';

import {HelpersModule} from './module';
import {createRegexMatchFormGroup, formValuesToFileFinderContentsRegexMatchCondition, RegexMatchCondition} from './regex_match_condition';

initTestEnvironment();

describe('RegexMatchCondition component', () => {
  let control: ReturnType<typeof createRegexMatchFormGroup>;

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
          teardown: {destroyAfterEach: false}
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
           .toBe(FileFinderContentsRegexMatchConditionMode.FIRST_HIT);
       expect(lengthField.nativeElement.value).toBe('20000000');
     });

  it('correctly exposes form values', async () => {
    const fixture = TestBed.createComponent(RegexMatchCondition);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();

    const regexFieldHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[name="regex"]'}));
    await regexFieldHarness.setValue('test');
    const modeFieldHarness = await loader.getHarness(MatSelectHarness);
    await modeFieldHarness.clickOptions({text: 'All Hits'});
    const lengthFieldHarness = await loader.getHarness(
        MatInputHarness.with({selector: '[name="length"]'}));
    await lengthFieldHarness.setValue('30000000');

    expect(control.value).toEqual({
      regex: 'test',
      mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
      length: 30000000,
    });
  });
});

describe('formValuesToFileFinderContentsRegexMatchCondition()', () => {
  it('correctly converts form value with decimal length', () => {
    const source = {
      regex: 'test',
      mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
      length: 20000000.999,
    };
    expect(formValuesToFileFinderContentsRegexMatchCondition(source)).toEqual({
      regex: btoa('test'),
      mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
      length: '20000000',
    });
  });
});
