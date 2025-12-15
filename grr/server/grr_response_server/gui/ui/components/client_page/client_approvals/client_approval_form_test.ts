import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../../../lib/api/http_api_with_translation_test_util';
import {ClientStore} from '../../../store/client_store';
import {GlobalStore} from '../../../store/global_store';
import {
  ClientStoreMock,
  GlobalStoreMock,
  newClientStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ClientApprovalForm} from './client_approval_form';
import {ClientApprovalFormHarness} from './testing/client_approval_form_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientApprovalForm);
  fixture.detectChanges();

  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientApprovalFormHarness,
  );
  return {fixture, harness};
}

describe('Client Approval Form', () => {
  let clientStoreMock: ClientStoreMock;
  let globalStoreMock: GlobalStoreMock;
  let httpApiServiceMock: HttpApiWithTranslationServiceMock;

  beforeEach(waitForAsync(() => {
    clientStoreMock = newClientStoreMock();
    globalStoreMock = newGlobalStoreMock();
    httpApiServiceMock = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      imports: [
        ClientApprovalForm,
        NoopAnimationsModule,
        RouterModule.forRoot([], {bindToComponentInputs: true}),
      ],
      providers: [
        {
          provide: ClientStore,
          useValue: clientStoreMock,
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useValue: httpApiServiceMock,
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness} = await createComponent();
    expect(harness).toBeDefined();
  });

  it('enables submit button when form is valid', async () => {
    clientStoreMock.clientId = signal('C.1234');
    const {harness} = await createComponent();

    await harness.setReason('Banana!!!');
    await harness.setAccessDuration('1h');

    expect(await harness.isSubmitButtonDisabled()).toBeFalse();
    expect(await harness.getSubmitButtonLabel()).toEqual('Request access');
  });

  it('disables submit button when form is submitted', async () => {
    clientStoreMock.clientId = signal('C.1234');
    const {harness} = await createComponent();

    await harness.setReason('Banana!!!');
    await harness.setAccessDuration('1h');
    await harness.submit();

    expect(await harness.isSubmitButtonDisabled()).toBeTrue();
    expect(await harness.getSubmitButtonLabel()).toEqual('Request sent');
  });

  it('shows error when no reason is provided', async () => {
    const {harness} = await createComponent();
    await harness.setReason('');

    expect(await harness.getReasonErrors()).toEqual(['Input is required.']);
    expect(await harness.isSubmitButtonDisabled()).toBeTrue();
  });

  it('shows error when no duration is provided', async () => {
    const {harness} = await createComponent();
    await harness.setAccessDuration('');

    expect(await harness.getAccessDurationErrors()).toEqual([
      'Input is required.',
    ]);
    expect(await harness.isSubmitButtonDisabled()).toBeTrue();
  });

  it('initializes duration input with default access duration', fakeAsync(async () => {
    globalStoreMock.uiConfig = signal({
      defaultAccessDurationSeconds: 60 * 60 * 24, // 1 day
    });
    const {harness} = await createComponent();

    expect(await harness.getAccessDuration()).toEqual('1 d');
  }));

  it('shows error when duration is longer than max duration', fakeAsync(async () => {
    globalStoreMock.uiConfig = signal({
      maxAccessDurationSeconds: 60 * 60 * 24, // 1 day
    });
    const {harness} = await createComponent();
    tick();
    await harness.setAccessDuration('4 d');

    expect(await harness.getAccessDurationErrors()).toEqual([
      'Maximum value is 86400.',
    ]);
    expect(await harness.isSubmitButtonDisabled()).toBeTrue();
  }));

  it('hides CC checkbox when optionalCcEmail is not set', fakeAsync(async () => {
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: undefined,
    });
    tick();
    const {harness} = await createComponent();

    expect(await harness.hasCcCheckbox()).toBeFalse();
  }));

  it('shows CC checkbox when optionalCcEmail is set', fakeAsync(async () => {
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: 'foo@bar.com',
    });
    tick();
    const {harness} = await createComponent();

    expect(await harness.hasCcCheckbox()).toBeTrue();
  }));

  it('checks CC checkbox by default', fakeAsync(async () => {
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: 'foo@bar.com',
    });
    tick();
    const {harness} = await createComponent();

    expect(await harness.isCcCheckboxChecked()).toBeTrue();
  }));

  it('sets reason for approval value in form based on url param', async () => {
    const router = TestBed.inject(Router);
    await router.navigate([], {
      queryParams: {'reason': 'foo/t/abcd'},
    });
    const {harness} = await createComponent();

    expect(await harness.getReason()).toEqual('foo/t/abcd');
  });

  it('correctly calls requestClientApproval when submitted with minimum required fields', async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));

    clientStoreMock.clientId = signal('C.1234');
    const {harness} = await createComponent();

    await harness.setReason('Banana!!!');
    await harness.setAccessDuration('1h');
    await harness.submit();

    expect(clientStoreMock.requestClientApproval).toHaveBeenCalledWith(
      'Banana!!!',
      [],
      1 * 60 * 60,
      [],
    );
  });

  it('correctly calls requestClientApproval when submitted with all fields set', fakeAsync(async () => {
    jasmine.clock().mockDate(new Date('2020-07-01T13:00:00.000+00:00'));
    clientStoreMock.clientId = signal('C.1234');
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: 'foo@bar.com',
    });
    tick();
    const {harness} = await createComponent();

    await harness.setReason('Banana!!!');
    const approverSuggestionSubform = await harness.approverSuggestionSubform();
    const approversAutocomplete =
      await approverSuggestionSubform.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next(['foo']);
    await approverSuggestionSubform.selectAutocompleteOption(
      'account_circle foo',
    );
    await harness.checkCcCheckbox();
    await harness.setAccessDuration('1h');
    await harness.submit();

    expect(clientStoreMock.requestClientApproval).toHaveBeenCalledWith(
      'Banana!!!',
      ['foo'],
      1 * 60 * 60,
      ['foo@bar.com'],
    );
  }));
});
