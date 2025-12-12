import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  ForemanClientRuleSet,
  ForemanClientRuleSetMatchMode,
  ForemanClientRuleType,
  ForemanIntegerClientRuleForemanIntegerField,
  ForemanIntegerClientRuleOperator,
  ForemanLabelClientRuleMatchMode,
  ForemanRegexClientRuleForemanStringField,
} from '../../../lib/api/api_interfaces';
import {GlobalStore} from '../../../store/global_store';
import {
  GlobalStoreMock,
  newGlobalStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {ClientsForm} from './clients_form';
import {ClientsFormHarness} from './testing/clients_form_harness';

initTestEnvironment();

async function createComponent(initialClientRuleSet?: ForemanClientRuleSet) {
  const fixture = TestBed.createComponent(ClientsForm);
  if (!initialClientRuleSet) {
    initialClientRuleSet = {
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
      rules: [],
    };
  }
  fixture.componentRef.setInput('initialRules', initialClientRuleSet);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientsFormHarness,
  );

  return {fixture, harness};
}

describe('Clients Form Component', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [ClientsForm, NoopAnimationsModule],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('can initialize the form state ', async () => {
    const {harness} = await createComponent({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ANY,
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: true, osLinux: true, osDarwin: false},
        },
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {
            labelNames: ['foo', 'bar'],
            matchMode: ForemanLabelClientRuleMatchMode.MATCH_ANY,
          },
        },
        {
          ruleType: ForemanClientRuleType.INTEGER,
          integer: {
            operator: ForemanIntegerClientRuleOperator.GREATER_THAN,
            value: '1337',
            field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
          },
        },
        {
          ruleType: ForemanClientRuleType.REGEX,
          regex: {
            attributeRegex: 'I am a regex',
            field: ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION,
          },
        },
      ],
    });

    const clientOsForms = await harness.clientOsForms();
    expect(clientOsForms.length).toBe(1);
    const windowsCheckbox = await clientOsForms[0].windowsCheckbox();
    expect(await windowsCheckbox.isChecked()).toBeTrue();
    const linuxCheckbox = await clientOsForms[0].linuxCheckbox();
    expect(await linuxCheckbox.isChecked()).toBeTrue();
    const darwinCheckbox = await clientOsForms[0].darwinCheckbox();
    expect(await darwinCheckbox.isChecked()).toBeFalse();

    const clientLabelsForms = await harness.clientLabelsForms();
    expect(clientLabelsForms.length).toBe(1);
    const labelNamesInputs = await clientLabelsForms[0].getLabelNames();
    expect(labelNamesInputs.length).toBe(2);
    expect(await labelNamesInputs[0]).toBe('foo');
    expect(await labelNamesInputs[1]).toBe('bar');

    const clientIntegerForms = await harness.clientIntegerForms();
    expect(clientIntegerForms.length).toBe(1);
    const operatorSelect = await clientIntegerForms[0].operatorSelect();
    expect(await operatorSelect.getValueText()).toBe('Greater Than');
    const valueInput = await clientIntegerForms[0].valueInput();
    expect(await valueInput.getValue()).toBe('1337');

    const clientRegexForms = await harness.clientRegexForms();
    expect(clientRegexForms.length).toBe(1);
    const regexInput = await clientRegexForms[0].regexInput();
    expect(await regexInput.getValue()).toBe('I am a regex');
  });

  it('renders the match button when there are more than 1 conditions', async () => {
    const {harness} = await createComponent({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
      rules: [
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {
            matchMode: ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY,
            labelNames: ['label-1', 'label-2'],
          },
        },
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: true, osLinux: true, osDarwin: false},
        },
      ],
    });

    const matchModeFormField = await harness.matchModeFormField();
    expect(matchModeFormField).not.toBeNull();

    const matchModeSelect =
      await matchModeFormField!.getControl(MatSelectHarness);
    expect(matchModeSelect).not.toBeNull();
    await matchModeSelect!.open();
    const options = await matchModeSelect!.getOptions();
    expect(options.length).toBe(2);
    expect(await options[0].getText()).toBe('Match All (and)');
    expect(await options[1].getText()).toBe('Match Any (or)');
  });

  it('can remove the condition on button click', async () => {
    const {harness} = await createComponent({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ANY,
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: true, osLinux: true, osDarwin: false},
        },
      ],
    });

    const removeRuleButtons = await harness.removeRuleButtons();
    expect(removeRuleButtons.length).toBe(1);
    const removeRuleButton = await harness.removeRuleButton(0);
    await removeRuleButton.click();

    const clientOsForms = await harness.clientOsForms();
    expect(clientOsForms.length).toBe(0);
  });

  it('does not render the match mode when there is no condition', async () => {
    const {harness} = await createComponent({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
      rules: [],
    });

    const matchModeFormField = await harness.matchModeFormField();
    expect(matchModeFormField).toBeNull();
  });

  it('adds a label form when clicking on "Labels" in menu', async () => {
    const {harness} = await createComponent();

    const addConditionButton = await harness.addConditionButton();
    await addConditionButton.click();
    const menu = await harness.addConditionMenu();
    await menu.open();
    const items = await menu.getItems({text: 'Labels'});
    await items[0].click();

    const clientLabelsForms = await harness.clientLabelsForms();
    expect(clientLabelsForms.length).toBe(1);
  });

  it('adds a integer form when clicking on "Client Version" in menu', async () => {
    const {harness} = await createComponent();

    const addConditionButton = await harness.addConditionButton();
    await addConditionButton.click();
    const menu = await harness.addConditionMenu();
    await menu.open();
    const items = await menu.getItems({text: 'Client Version'});
    await items[0].click();

    const clientIntegerForms = await harness.clientIntegerForms();
    expect(clientIntegerForms.length).toBe(1);
  });

  it('adds a regex form when clicking on "Client Description" in menu', async () => {
    const {harness} = await createComponent();

    const addConditionButton = await harness.addConditionButton();
    await addConditionButton.click();
    const menu = await harness.addConditionMenu();
    await menu.open();
    const items = await menu.getItems({text: 'Client Description'});
    await items[0].click();

    const clientRegexForms = await harness.clientRegexForms();
    expect(clientRegexForms.length).toBe(1);
  });

  it('can build the form state', async () => {
    const {fixture} = await createComponent({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: false, osLinux: false, osDarwin: false},
        },
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {
            matchMode: ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY,
            labelNames: ['foo', 'bar'],
          },
        },
        {
          ruleType: ForemanClientRuleType.INTEGER,
          integer: {
            operator: ForemanIntegerClientRuleOperator.GREATER_THAN,
            value: '1337',
            field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
          },
        },
        {
          ruleType: ForemanClientRuleType.REGEX,
          regex: {
            attributeRegex: 'I am a regex.*',
            field: ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION,
          },
        },
      ],
    });

    expect(fixture.componentInstance.getFormState()).toEqual({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL, // Default
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: false, osLinux: false, osDarwin: false},
        },
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {
            labelNames: ['foo', 'bar'],
            matchMode: ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY,
          },
        },
        {
          ruleType: ForemanClientRuleType.INTEGER,
          integer: {
            operator: ForemanIntegerClientRuleOperator.GREATER_THAN,
            value: '1337',
            field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_VERSION,
          },
        },
        {
          ruleType: ForemanClientRuleType.REGEX,
          regex: {
            attributeRegex: 'I am a regex.*',
            field: ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION,
          },
        },
      ],
    });
  });

  it('reset button resets the form to the initial values', async () => {
    const {harness} = await createComponent({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ANY,
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: true, osLinux: true, osDarwin: true},
        },
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {
            matchMode: ForemanLabelClientRuleMatchMode.DOES_NOT_MATCH_ANY,
            labelNames: ['foo', 'bar'],
          },
        },
      ],
    });

    const removeRuleButtons = await harness.removeRuleButtons();
    await removeRuleButtons[0].click();
    const resetButton = await harness.resetButton();
    await resetButton.click();

    expect(await harness.getMatchMode()).toBe('Match Any (or)');
    expect(await harness.clientOsForms()).toHaveSize(1);
    expect(await harness.clientLabelsForms()).toHaveSize(1);
    expect(await harness.clientIntegerForms()).toHaveSize(0);
    expect(await harness.clientRegexForms()).toHaveSize(0);
  });

  it('shows presubmit warning when the rules are not valid', async () => {
    globalStoreMock.uiConfig = signal({
      huntConfig: {
        presubmitWarningMessage: 'you shall not pass',
        defaultExcludeLabels: ['no', 'also-no'],
        presubmitCheckWithSkipTag: 'SKIP_PRESUBMIT_CHECK',
      },
    });
    const {harness} = await createComponent();

    const warningCard = await harness.warningCard();
    expect(warningCard).not.toBeNull();
    expect(await warningCard!.getText()).toContain('you shall not pass');
    expect(await warningCard!.getText()).toContain('SKIP_PRESUBMIT_CHECK');
    expect(await warningCard!.getText()).toContain('no');
    expect(await warningCard!.getText()).toContain('also-no');
  });

  it('adds the label form with the expected excluded labels when clicking on the fix button', async () => {
    globalStoreMock.uiConfig = signal({
      huntConfig: {
        presubmitWarningMessage: 'you shall not pass',
        defaultExcludeLabels: ['no', 'also-no'],
        presubmitCheckWithSkipTag: 'SKIP_PRESUBMIT_CHECK',
      },
    });
    const {harness} = await createComponent();

    const fixButton = await harness.fixButton();
    await fixButton!.click();

    const labelForm = await harness.clientLabelsForms();
    expect(labelForm).toHaveSize(1);
    const labelNamesInputs = await labelForm[0].getLabelNames();
    expect(labelNamesInputs).toEqual(['no', 'also-no']);
    expect(await harness.warningCard()).toBeNull();
  });

  it('does not show presubmit warning when the rules are valid', async () => {
    globalStoreMock.uiConfig = signal({
      huntConfig: {
        presubmitWarningMessage: 'you shall not pass',
        defaultExcludeLabels: ['no', 'also-no'],
        presubmitCheckWithSkipTag: 'SKIP_PRESUBMIT_CHECK',
      },
    });
    const {harness} = await createComponent();

    const addConditionButton = await harness.addConditionButton();
    await addConditionButton.click();
    const addConditionMenu = await harness.addConditionMenu();
    await addConditionMenu.open();
    const items = await addConditionMenu.getItems({text: 'Labels'});
    await items[0].click();
    const clientLabelsForms = await harness.clientLabelsForms();
    expect(clientLabelsForms).toHaveSize(1);
    await clientLabelsForms[0].setMatchMode("Doesn't match any");
    const addLabelButton = await clientLabelsForms[0].addLabelButton();
    await addLabelButton.click();
    await clientLabelsForms[0].setLabel(0, 'no');
    await addLabelButton.click();
    await clientLabelsForms[0].setLabel(1, 'also-no');

    expect(await harness.warningCard()).toBeNull();
  });
});
