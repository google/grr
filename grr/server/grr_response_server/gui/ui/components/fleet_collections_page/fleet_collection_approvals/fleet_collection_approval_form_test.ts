import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../../../lib/api/http_api_with_translation_test_util';
import {FleetCollectionStore} from '../../../store/fleet_collection_store';
import {GlobalStore} from '../../../store/global_store';
import {
  FleetCollectionStoreMock,
  GlobalStoreMock,
  newFleetCollectionStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {FleetCollectionApprovalForm} from './fleet_collection_approval_form';
import {FleetCollectionApprovalFormHarness} from './testing/fleet_collection_approval_form_harness';

initTestEnvironment();

async function createComponent(fleetCollectionId = '1234') {
  const fixture = TestBed.createComponent(FleetCollectionApprovalForm);
  fixture.componentRef.setInput('fleetCollectionId', fleetCollectionId);

  fixture.detectChanges();

  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionApprovalFormHarness,
  );
  return {fixture, harness};
}

describe('Fleet Collection Approval Form', () => {
  let fleetCollectionStoreMock: FleetCollectionStoreMock;
  let globalStoreMock: GlobalStoreMock;
  let httpApiServiceMock: HttpApiWithTranslationServiceMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionStoreMock = newFleetCollectionStoreMock();
    globalStoreMock = newGlobalStoreMock();
    httpApiServiceMock = mockHttpApiWithTranslationService();

    TestBed.configureTestingModule({
      imports: [
        FleetCollectionApprovalForm,
        NoopAnimationsModule,
        RouterModule.forRoot([], {bindToComponentInputs: true}),
      ],
      providers: [
        {
          provide: FleetCollectionStore,
          useValue: fleetCollectionStoreMock,
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
    const {harness} = await createComponent('ABCD1234');

    await harness.setReason('Banana!!!');

    expect(await harness.isSubmitButtonDisabled()).toBeFalse();
    expect(await harness.getSubmitButtonLabel()).toEqual('Request access');
  });

  it('disables submit button when form is submitted', async () => {
    const {harness} = await createComponent();

    await harness.setReason('Banana!!!');
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

  it('hides CC checkbox when optionalCcEmail is not set', fakeAsync(async () => {
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: undefined,
    });
    const {harness} = await createComponent();

    expect(await harness.hasCcCheckbox()).toBeFalse();
  }));

  it('shows CC checkbox when optionalCcEmail is set', fakeAsync(async () => {
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: 'foo@bar.com',
    });
    const {harness} = await createComponent();

    expect(await harness.hasCcCheckbox()).toBeTrue();
  }));

  it('checks CC checkbox by default', fakeAsync(async () => {
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: 'foo@bar.com',
    });
    const {harness} = await createComponent();

    expect(await harness.isCcCheckboxChecked()).toBeTrue();
  }));

  it('correctly calls requestFleetCollectionApproval when submitted with all fields set', fakeAsync(async () => {
    globalStoreMock.approvalConfig = signal({
      optionalCcEmail: 'foo@bar.com',
    });
    const {harness} = await createComponent('ABCD1234');

    const approverSuggestionSubform = await harness.approverSuggestionSubform();
    const approversAutocomplete =
      await approverSuggestionSubform.approversAutocomplete();
    await approversAutocomplete.enterText('foo');
    httpApiServiceMock.mockedObservables.suggestApprovers.next(['foo']);
    await approverSuggestionSubform.selectAutocompleteOption(
      'account_circle foo',
    );
    await harness.setReason('Banana!!!');
    await harness.checkCcCheckbox();
    await harness.submit();

    expect(
      fleetCollectionStoreMock.requestFleetCollectionApproval,
    ).toHaveBeenCalledWith('ABCD1234', 'Banana!!!', ['foo'], ['foo@bar.com']);
  }));
});
