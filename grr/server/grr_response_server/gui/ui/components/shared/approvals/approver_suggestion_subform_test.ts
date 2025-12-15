import {TestKey} from '@angular/cdk/testing';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {FormGroup, ReactiveFormsModule} from '@angular/forms';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../../../lib/api/http_api_with_translation_test_util';
import {initTestEnvironment} from '../../../testing';
import {
  ApproverSuggestionSubform,
  createApproverSuggestionFormGroup,
} from './approver_suggestion_subform';
import {ApproverSuggestionSubformHarness} from './testing/approver_suggestion_subform_harness';

initTestEnvironment();

@Component({
  selector: 'approver-suggestion-subform-test',
  template: `
    <form [formGroup]="formGroup">
      <approver-suggestion-subform
          [formGroup]="formGroup.controls.approvers_form"/>
    </form>
  `,
  imports: [CommonModule, ApproverSuggestionSubform, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
class TestComponent {
  readonly formGroup = new FormGroup({
    approvers_form: createApproverSuggestionFormGroup(),
  });
}

async function createComponent() {
  const fixture = TestBed.createComponent(TestComponent);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ApproverSuggestionSubformHarness,
  );
  return {fixture, harness};
}

describe('Approver Suggestion Subform component', () => {
  let httpApiServiceMock: HttpApiWithTranslationServiceMock;

  beforeEach(waitForAsync(() => {
    httpApiServiceMock = mockHttpApiWithTranslationService();
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ApproverSuggestionSubform],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useValue: httpApiServiceMock,
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('fetches autocomplete suggestions from api when input is changed', fakeAsync(async () => {
    const {harness} = await createComponent();

    const approversAutocomplete = await harness.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'foo',
      'foobar',
    ]);
    expect(httpApiServiceMock.suggestApprovers).toHaveBeenCalledWith('f');
    expect(httpApiServiceMock.suggestApprovers).toHaveBeenCalledWith('fo');
    expect(httpApiServiceMock.suggestApprovers).toHaveBeenCalledWith('foo');

    expect(await harness.getAutocompleteOptions()).toEqual([
      'account_circle foo',
      'account_circle foobar',
    ]);
  }));

  it('adds selected autocomplete suggestion to approvers', fakeAsync(async () => {
    const {harness} = await createComponent();

    const approversAutocomplete = await harness.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'foo',
      'foobar',
    ]);
    await harness.selectAutocompleteOption('account_circle foo');

    expect(await harness.getApprovers()).toEqual(['foo']);
    const input = await harness.getApproversInputHarness();
    expect(await input!.getValue()).toEqual('');
  }));

  it('filters suggestions based on already selected approvers', fakeAsync(async () => {
    const {harness} = await createComponent();

    const approversAutocomplete = await harness.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'foo',
      'foobar',
    ]);
    await harness.selectAutocompleteOption('account_circle foo');

    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'foo',
      'foobar',
    ]);

    expect(await harness.getAutocompleteOptions()).toEqual([
      'account_circle foobar',
      // filtered out 'account_circle foo'
    ]);
  }));

  it('adds inputted approver to approvers if in suggestions and prunes input field', fakeAsync(async () => {
    const {harness} = await createComponent();

    const approversAutocomplete = await harness.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'foo',
      'foobar',
    ]);
    const input = await harness.getApproversInputHarness();
    await input!.setValue('foo');
    await input!.sendSeparatorKey(TestKey.ENTER);

    expect(await harness.getApprovers()).toEqual(['foo']);
    expect(await input!.getValue()).toEqual('');
  }));

  it('does not add inputted approver to approvers if not in suggestions', fakeAsync(async () => {
    const {harness} = await createComponent();

    const approversAutocomplete = await harness.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'foo',
      'foobar',
    ]);
    const input = await harness.getApproversInputHarness();
    await input!.setValue('baz');
    await input!.sendSeparatorKey(TestKey.ENTER);

    expect(await harness.getApprovers()).toEqual([]);
    expect(await input!.getValue()).toEqual('baz');
  }));

  it('can add several approvers', fakeAsync(async () => {
    const {harness} = await createComponent();

    const approversAutocomplete = await harness.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'foo',
      'foobar',
    ]);
    await harness.selectAutocompleteOption('account_circle foo');

    await approversAutocomplete.enterText('bar');
    httpApiServiceMock.mockedObservables.suggestApprovers.next([
      'bar',
      'foobar',
    ]);
    await harness.selectAutocompleteOption('account_circle bar');

    expect(await harness.getApprovers()).toEqual(['foo', 'bar']);
  }));

  it('correctly exposes form value', async () => {
    const {harness, fixture} = await createComponent();

    const approversAutocomplete = await harness.approversAutocomplete();
    await approversAutocomplete.enterText('b');
    httpApiServiceMock.mockedObservables.suggestApprovers.next(['bar', 'baz']);
    const input = await harness.getApproversInputHarness();
    await input!.setValue('baz');
    await input!.sendSeparatorKey(TestKey.ENTER);

    expect(fixture.componentInstance.formGroup.value.approvers_form).toEqual({
      approvers: ['baz'],
      input: '',
    });
  });
});
