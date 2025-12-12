import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MAT_DIALOG_DATA} from '@angular/material/dialog';
import {
  MatTestDialogOpener,
  MatTestDialogOpenerModule,
} from '@angular/material/dialog/testing';

import {Browser} from '../../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {
  FLOW_DETAILS_BY_TYPE,
  FlowCategory,
} from '../../../lib/data/flows/flow_definitions';
import {FlowType} from '../../../lib/models/flow';
import {newGrrUser} from '../../../lib/models/model_test_util';
import {GlobalStore} from '../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CreateFlowDialog, CreateFlowDialogData} from './create_flow_dialog';
import {CreateFlowDialogHarness} from './testing/create_flow_dialog_harness';

initTestEnvironment();

async function createDialog(dialogData: CreateFlowDialogData) {
  const opener = MatTestDialogOpener.withComponent<
    CreateFlowDialog,
    CreateFlowDialogData
  >(CreateFlowDialog, {data: dialogData});

  const fixture = TestBed.createComponent(opener);
  fixture.autoDetectChanges();
  const loader = TestbedHarnessEnvironment.documentRootLoader(fixture);
  const dialogHarness = await loader.getHarness(CreateFlowDialogHarness);
  return {fixture, dialogHarness};
}

describe('Create Flow Dialog', () => {
  let onSubmitSpy: jasmine.Spy<CreateFlowDialogData['onSubmit']>;
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    onSubmitSpy = jasmine.createSpy('onSubmit');
    globalStoreMock = newGlobalStoreMock();
    TestBed.configureTestingModule({
      imports: [
        CreateFlowDialog,
        ReactiveFormsModule,
        MatTestDialogOpenerModule,
      ],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: {
            onSubmit: onSubmitSpy,
          },
        },
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => mockHttpApiWithTranslationService(),
        },
      ],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createDialog({
      onSubmit: onSubmitSpy,
    });

    expect(fixture).toBeTruthy();
  });

  it('does not call `onSubmit` when closed', async () => {
    const {fixture, dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    expect(fixture.componentInstance.closedResult).toBeUndefined();

    await dialogHarness.close();
    expect(onSubmitSpy).not.toHaveBeenCalled();
  });

  it('initially shows available flows and flow search', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    expect(await dialogHarness.showsFlowCategories()).toBeTrue();
    expect(await dialogHarness.showsAutocompleteInput()).toBeTrue();
  });

  it('shows popular flows', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });

    expect(
      await dialogHarness.hasFlowButton(/Collect a forensic artifact/),
    ).toBeTrue();
    expect(
      await dialogHarness.hasFlowButton(/Collect browser history/),
    ).toBeTrue();
    expect(await dialogHarness.hasFlowButton(/Interrogate/)).toBeTrue();
    expect(await dialogHarness.hasFlowButton(/Osquery/)).toBeTrue();
    expect(
      await dialogHarness.hasFlowButton(/Collect path timeline/),
    ).toBeTrue();
  });

  it('initially does not show flow args form', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    expect(await dialogHarness.showsFlowArgsForm()).toBeFalse();
  });

  it('immediately shows flow args form when flow type is passed in the dialog data', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
      flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
    });
    expect(await dialogHarness.showsFlowArgsForm()).toBeTrue();
  });

  it('passes flow args to the flow args form', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
      flowType: FlowType.COLLECT_BROWSER_HISTORY,
      flowArgs: {
        browsers: [Browser.FIREFOX, Browser.SAFARI],
      },
    });
    const flowArgsForm = await dialogHarness.getFlowArgsForm();
    expect(await flowArgsForm.collectBrowserHistoryForm()).toBeDefined();
    const collectBrowserHistoryForm =
      await flowArgsForm.collectBrowserHistoryForm();
    const firefoxCheckbox = await collectBrowserHistoryForm.firefoxCheckbox();
    expect(await firefoxCheckbox.isChecked()).toBeTrue();
    const safariCheckbox = await collectBrowserHistoryForm.safariCheckbox();
    expect(await safariCheckbox.isChecked()).toBeTrue();
    const chromeCheckbox =
      await collectBrowserHistoryForm.chromiumBasedBrowsersCheckbox();
    expect(await chromeCheckbox.isChecked()).toBeFalse();
  });

  it('unchecks disableRrgSupport by default', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
      flowType: FlowType.ARTIFACT_COLLECTOR_FLOW,
    });
    const disableRrgSupportCheckbox =
      await dialogHarness.disableRrgSupportCheckbox();

    expect(await disableRrgSupportCheckbox.isChecked()).toBeFalse();
  });

  it('sets disableRrgSupport to false when the checkbox is not checked', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
      flowType: FlowType.INTERROGATE,
    });

    const flowArgsForm = await dialogHarness.getFlowArgsForm();
    const interrogateForm = await flowArgsForm.interrogateForm();
    const submitButton = await interrogateForm.getSubmitButton();

    await submitButton.submit();

    expect(onSubmitSpy).toHaveBeenCalledWith(
      'Interrogate',
      jasmine.anything(),
      false,
    );
  });

  it('sets disableRrgSupport to true when the checkbox is checked', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
      flowType: FlowType.INTERROGATE,
    });
    const disableRrgSupportCheckbox =
      await dialogHarness.disableRrgSupportCheckbox();
    await disableRrgSupportCheckbox.check();

    const flowArgsForm = await dialogHarness.getFlowArgsForm();
    const interrogateForm = await flowArgsForm.interrogateForm();
    const submitButton = await interrogateForm.getSubmitButton();
    await submitButton.submit();

    expect(onSubmitSpy).toHaveBeenCalledWith(
      'Interrogate',
      jasmine.anything(),
      true,
    );
  });

  it('filters available flows based on name in the search options', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    const autocompleteSearchHarness = await dialogHarness.autocompleteHarness();
    await autocompleteSearchHarness?.enterText(
      FLOW_DETAILS_BY_TYPE.get(FlowType.ARTIFACT_COLLECTOR_FLOW)!.friendlyName,
    );
    tick();

    const options = await autocompleteSearchHarness?.getOptions();
    expect(options!.length).toBe(1);

    expect(await options![0].getText()).toContain('artifact');
  }));

  it('filters available flows based on category in the search options', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    const autocompleteSearchHarness = await dialogHarness.autocompleteHarness();
    await autocompleteSearchHarness?.enterText(FlowCategory.BROWSER);
    tick();

    const filteredOptions = await autocompleteSearchHarness?.getOptions();
    expect(filteredOptions!.length).toBe(1);
    expect(await filteredOptions![0].getText()).toContain('browser');
  }));

  it('filters available flows based on description in the search options', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    const autocompleteSearchHarness = await dialogHarness.autocompleteHarness();
    await autocompleteSearchHarness?.enterText(
      FLOW_DETAILS_BY_TYPE.get(FlowType.ARTIFACT_COLLECTOR_FLOW)!.description,
    );
    tick();

    const options = await autocompleteSearchHarness?.getOptions();
    expect(options!.length).toBe(1);
    expect(await options![0].getText()).toContain('artifact');
  }));

  it('can select flow via flow button', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });

    await dialogHarness.openFlowCategory('Collectors');
    const flowButton = await dialogHarness.getFlowButton(
      /.*Collect a forensic artifact/,
    );
    await flowButton.click();
    expect(await dialogHarness.showsFlowArgsForm()).toBeTrue();
  });

  it('disables buttons of restricted flows for non-admin users', async () => {
    globalStoreMock.currentUser = signal(newGrrUser({isAdmin: false}));
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });

    await dialogHarness.openFlowCategory('Administrative');
    const flowButton = await dialogHarness.getFlowButton(
      /.*Execute Python hack/,
    );
    expect(await flowButton.isDisabled()).toBeTrue();
  });

  it('shows flow args form when flow is selected via autocomplete', fakeAsync(async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    const autocompleteSearchHarness = await dialogHarness.autocompleteHarness();
    await autocompleteSearchHarness?.enterText('collect a forensic artifact');
    tick();
    const flowOptions = await autocompleteSearchHarness?.getOptions();
    // There should be only one flow option, the artifact collector flow.
    expect(flowOptions!.length).toBe(1);
    await flowOptions![0]!.click();

    expect(await dialogHarness.showsFlowCategories()).toBeFalse();
    expect(await dialogHarness.showsFlowArgsForm()).toBeTrue();
    const flowArgsForm = await dialogHarness.getFlowArgsForm();
    expect(await flowArgsForm.artifactCollectorFlowForm()).toBeDefined();
  }));

  it('does not show back button when flow is not selected', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    expect(await dialogHarness.backButton()).toBeNull();
  });

  it('shows back button when flow is selected', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    await dialogHarness.openFlowCategory('Collectors');
    const flowButton = await dialogHarness.getFlowButton(
      /.*Collect a forensic artifact/,
    );
    await flowButton.click();

    expect(await dialogHarness.backButton()).not.toBeNull();
  });

  it('shows initial flow type selection when clicking on reset flow type button', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    // Select any flow type.
    await dialogHarness.openFlowCategory('Collectors');
    const flowButton = await dialogHarness.getFlowButton(
      /.*Collect a forensic artifact/,
    );
    await flowButton.click();
    const backButton = await dialogHarness.backButton();
    expect(backButton).not.toBeNull();
    await backButton!.click();

    expect(await dialogHarness.showsAutocompleteInput()).toBeTrue();
    expect(await dialogHarness.showsFlowCategories()).toBeTrue();
    expect(await dialogHarness.showsFlowArgsForm()).toBeFalse();
  });

  it('hides hidden flows in the autocomplete and flow buttons', async () => {
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });
    // Precondition: the knowledgebase flow should be hidden.
    expect(
      FLOW_DETAILS_BY_TYPE.get(FlowType.KNOWLEDGE_BASE_INITIALIZATION_FLOW)!
        .hidden,
    ).toBeTrue();

    const autocompleteSearchHarness = await dialogHarness.autocompleteHarness();
    await autocompleteSearchHarness?.enterText('knowledgebase');

    expect(await autocompleteSearchHarness?.isOpen()).toBeFalse();
    const hasKnowledgebaseFlowButton =
      await dialogHarness.hasFlowButton(/.*Knowledgebase/);
    expect(hasKnowledgebaseFlowButton).toBeFalse();
  });

  it('disables restricted flows in the autocomplete for non-admin users', async () => {
    globalStoreMock.currentUser = signal(newGrrUser({isAdmin: false}));
    const {dialogHarness} = await createDialog({
      onSubmit: onSubmitSpy,
    });

    const autocompleteSearchHarness = await dialogHarness.autocompleteHarness();
    await autocompleteSearchHarness?.enterText('python hack');

    const flowOptions = await autocompleteSearchHarness?.getOptions();
    expect(flowOptions!.length).toBe(1);
    expect(await flowOptions![0].isDisabled()).toBeTrue();
  });
});
