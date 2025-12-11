import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileFinderContentsRegexMatchConditionMode} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {
  createRegexMatchFormGroup,
  RegexMatchSubform,
} from './regex_match_subform';
import {RegexMatchSubformHarness} from './testing/regex_match_subform_harness';

initTestEnvironment();

@Component({
  selector: 'regex-match-subform-test',
  template: `
    <form [formGroup]="formGroup">
      <regex-match-subform [formGroup]="formGroup.controls.regexMatch"/>
    </form>
  `,
  imports: [CommonModule, RegexMatchSubform, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
class TestComponent {
  readonly formGroup = new FormGroup({
    regexMatch: createRegexMatchFormGroup(),
  });
}

async function createComponent() {
  const fixture = TestBed.createComponent(TestComponent);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    RegexMatchSubformHarness,
  );
  return {fixture, harness};
}

describe('Regex Match Subform component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, RegexMatchSubform],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('displays empty regex field and correctly filled mode and length fields when initialized', async () => {
    const {harness} = await createComponent();

    const regexField = await harness.regexInput();
    expect(await regexField.getValue()).toBe('');

    const modeField = await harness.modeSelect();
    expect(await modeField.getValueText()).toBe('First Hit');

    const lengthField = await harness.lengthInput();
    expect(await lengthField.getValue()).toBe('20000000');
  });

  it('correctly exposes form values', async () => {
    const {harness, fixture} = await createComponent();

    const regexField = await harness.regexInput();
    await regexField.setValue('test');
    const modeField = await harness.modeSelect();
    await modeField.clickOptions({text: 'All Hits'});
    const lengthField = await harness.lengthInput();
    await lengthField.setValue('30000000');

    expect(fixture.componentInstance.formGroup.value?.regexMatch).toEqual({
      regex: 'test',
      mode: FileFinderContentsRegexMatchConditionMode.ALL_HITS,
      length: 30000000,
    });
  });
});
