import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {FileFinderContentsLiteralMatchConditionMode} from '../../../../lib/api/api_interfaces';
import {initTestEnvironment} from '../../../../testing';
import {
  createLiteralMatchFormGroup,
  LiteralMatchSubform,
} from './literal_match_subform';
import {LiteralMatchSubformHarness} from './testing/literal_match_subform_harness';

initTestEnvironment();

@Component({
  selector: 'literal-match-subform-test',
  template: `
    <form [formGroup]="formGroup">
      <literal-match-subform [formGroup]="formGroup.controls.literalMatch"/>
    </form>
  `,
  imports: [CommonModule, LiteralMatchSubform, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
class TestComponent {
  readonly formGroup = new FormGroup({
    literalMatch: createLiteralMatchFormGroup(),
  });
}

async function createComponent() {
  const fixture = TestBed.createComponent(TestComponent);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    LiteralMatchSubformHarness,
  );
  return {fixture, harness};
}

describe('Literal Match Subform component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, LiteralMatchSubform],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('displays empty literal field and correctly filled mode field when initialized', async () => {
    const {harness} = await createComponent();

    const literalInput = await harness.literalInput();
    expect(await literalInput.getValue()).toBe('');

    const modeSelect = await harness.modeSelect();
    expect(await modeSelect.getValueText()).toBe('First Hit');
  });

  it('correctly exposes form value', async () => {
    const {harness, fixture} = await createComponent();

    const literalInput = await harness.literalInput();
    await literalInput.setValue('test');
    const modeSelect = await harness.modeSelect();
    await modeSelect.clickOptions({text: 'All Hits'});

    expect(fixture.componentInstance.formGroup.value.literalMatch).toEqual({
      literal: 'test',
      mode: FileFinderContentsLiteralMatchConditionMode.ALL_HITS,
    });
  });
});
