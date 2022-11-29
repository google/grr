import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ForemanClientRuleSetMatchMode, ForemanClientRuleType, ForemanIntegerClientRuleForemanIntegerField, ForemanIntegerClientRuleOperator, ForemanLabelClientRuleMatchMode, ForemanRegexClientRuleForemanStringField} from '../../../../lib/api/api_interfaces';
import {ConfigGlobalStore} from '../../../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../../../testing';

import {ClientsForm} from './clients_form';
import {ClientsFormModule} from './module';

initTestEnvironment();

async function setInputValue(
    fixture: ComponentFixture<unknown>, query: string, value: string) {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const inputHarness =
      await harnessLoader.getHarness(MatInputHarness.with({selector: query}));
  await inputHarness.setValue(value);
}

async function getInputValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<string> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const inputHarness =
      await harnessLoader.getHarness(MatInputHarness.with({selector: query}));
  return await inputHarness.getValue();
}

async function setCheckboxValue(
    fixture: ComponentFixture<unknown>, query: string, value: boolean) {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const checkboxHarness = await harnessLoader.getHarness(
      MatCheckboxHarness.with({selector: query}));
  if (value) {
    await checkboxHarness.check();
  } else {
    await checkboxHarness.uncheck();
  }
}

async function getCheckboxValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<boolean> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const checkboxHarness = await harnessLoader.getHarness(
      MatCheckboxHarness.with({selector: query}));
  return await checkboxHarness.isChecked();
}

async function selectMenuOption(menuHarness: MatMenuHarness, index: number) {
  await menuHarness.open();
  const items = await menuHarness.getItems();
  await items[index].click();
}

async function selectBoxOption(
    fixture: ComponentFixture<unknown>, query: string, value: string) {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const selectionBoxHarness =
      await harnessLoader.getHarness(MatSelectHarness.with({selector: query}));
  await selectionBoxHarness.clickOptions({text: value});
}

async function getSelectBoxValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<string> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const selectionBoxHarness =
      await harnessLoader.getHarness(MatSelectHarness.with({selector: query}));
  return await selectionBoxHarness.getValueText();
}

describe('clients form test', () => {
  let configGlobalStoreMock: ConfigGlobalStoreMock;
  beforeEach(waitForAsync(() => {
    configGlobalStoreMock = mockConfigGlobalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ClientsFormModule,
          ],
          providers: [{
            provide: ConfigGlobalStore,
            useFactory: () => configGlobalStoreMock
          }],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('toggles contents on click on toggle button', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    const button = fixture.debugElement.query(By.css('#client-form-toggle'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('opens contents on click on header', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    const button = fixture.debugElement.query(By.css('#client-form-toggle'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();

    const header = fixture.debugElement.query(By.css('.header'));
    header.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('only renders the match button when there are several conditions',
     async () => {
       const fixture = TestBed.createComponent(ClientsForm);
       fixture.detectChanges();
       expect(fixture.debugElement.query(By.css('.match-condition')))
           .toBeNull();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const menu = await loader.getHarness(MatMenuHarness);
       await menu.open();
       const items = await menu.getItems();
       await items[0].click();
       expect(fixture.debugElement.query(By.css('.match-condition')))
           .not.toBeNull();
     });

  it('renders an os form by default', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Operating System');
  });

  it('deletes the form when clicking cancel', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();
    const before = fixture.debugElement.nativeElement.textContent;
    expect(before).toContain('Operating System');

    const button = fixture.debugElement.query(By.css('#close'));
    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    const after = fixture.debugElement.nativeElement.textContent;
    expect(after).not.toContain('Operating System');
  });

  it('adds a label form when clicking on Label in menu', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[1].click();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Label');
    expect(fixture.componentInstance.conditions().controls.length).toBe(2);
  });

  it('adds and deletes label name input when clicking on add and delete button',
     async () => {
       const fixture = TestBed.createComponent(ClientsForm);
       fixture.detectChanges();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const menu = await loader.getHarness(MatMenuHarness);
       await menu.open();
       const items = await menu.getItems();
       await items[1].click();
       const text = fixture.debugElement.nativeElement.textContent;
       expect(text).toContain('Label');
       expect(fixture.componentInstance.conditions().controls.length).toBe(2);
       expect(fixture.componentInstance.labelNames(1).controls.length).toBe(1);
       const button = fixture.debugElement.query(By.css('#add-label-name'));
       button.triggerEventHandler('click', new MouseEvent('click'));
       fixture.detectChanges();
       expect(fixture.componentInstance.labelNames(1).controls.length).toBe(2);
       const deleteButton =
           fixture.debugElement.query(By.css('#remove-label-name'));
       deleteButton.triggerEventHandler('click', new MouseEvent('click'));
       fixture.detectChanges();
       expect(fixture.componentInstance.labelNames(1).controls.length).toBe(1);
     });

  it('adds a integer form when clicking on Client Clock in menu', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[4].click();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Client Clock');
    expect(fixture.debugElement.query(By.css('.operator'))).not.toBeNull();
    expect(fixture.componentInstance.conditions().controls.length).toBe(2);
  });

  it('adds a regex form when clicking on Client Description in menu',
     async () => {
       const fixture = TestBed.createComponent(ClientsForm);
       fixture.detectChanges();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const menu = await loader.getHarness(MatMenuHarness);
       await menu.open();
       const items = await menu.getItems();
       await items[5].click();
       const text = fixture.debugElement.nativeElement.textContent;
       expect(text).toContain('Client Description');
       expect(fixture.debugElement.query(By.css('.attribute-regex')))
           .not.toBeNull();
       expect(fixture.componentInstance.conditions().controls.length).toBe(2);
     });

  it('builds correct rule set using the form values', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[5].click();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Client Description');
    expect(fixture.debugElement.query(By.css('.attribute-regex')))
        .not.toBeNull();
    expect(fixture.componentInstance.conditions().controls.length).toBe(2);
  });

  it('buildRules builds ForemanRuleSet using the form values', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);

    // OS rule is rendered by default
    await setCheckboxValue(fixture, '[id=condition_0_windows]', true);

    await selectMenuOption(menu, 1);  // adds Labels form
    await selectBoxOption(fixture, '[id=condition_1_match_mode]', 'Match any');
    await setInputValue(fixture, 'input[id=condition_1_label_name_0]', 'foo');
    const addLabelButton =
        fixture.debugElement.query(By.css('#add-label-name'));
    addLabelButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    await setInputValue(fixture, 'input[id=condition_1_label_name_1]', 'bar');

    await selectMenuOption(menu, 4);  // adds Client Clock integer form
    await selectBoxOption(fixture, '[id=condition_2_operator]', 'Greater Than');
    await setInputValue(fixture, 'input[id=condition_2_integer_value]', '123');

    await selectMenuOption(menu, 5);  // adds Client Description regex form
    await setInputValue(
        fixture, 'input[id=condition_3_regex_value]', 'I am a regex');
    fixture.detectChanges();

    expect(fixture.componentInstance.buildRules()).toEqual({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,  // Default
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: true, osLinux: false, osDarwin: false},
        },
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {
            labelNames: ['foo', 'bar'],
            matchMode: ForemanLabelClientRuleMatchMode.MATCH_ANY
          },
        },
        {
          ruleType: ForemanClientRuleType.INTEGER,
          integer: {
            operator: ForemanIntegerClientRuleOperator.GREATER_THAN,
            value: '123',
            field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_CLOCK
          },
        },
        {
          ruleType: ForemanClientRuleType.REGEX,
          regex: {
            attributeRegex: 'I am a regex',
            field: ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION
          },
        },
      ]
    });
  });

  it('buildRules builds with rule match ALL by default', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    expect(fixture.componentInstance.buildRules())
        .toEqual(jasmine.objectContaining({
          matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
        }));
  });

  it('buildRules builds with rule match ANY', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    // This only shows when there is more than one condition, so we add one here
    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await selectMenuOption(menu, 1);

    await selectBoxOption(fixture, '[id=rulesMatchMode]', 'Match Any (or)');
    fixture.detectChanges();

    expect(fixture.componentInstance.buildRules())
        .toEqual(jasmine.objectContaining({
          matchMode: ForemanClientRuleSetMatchMode.MATCH_ANY,
        }));
  });

  it('shows autocomplete options correctly', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    configGlobalStoreMock.mockedObservables.clientsLabels$.next([
      'label1',
      'unusedlabel',
      'testlabel',
    ]);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[1].click();
    const labelName = fixture.debugElement.query(By.css('.label-name'))
                          .query(By.css('input'));
    labelName.nativeElement.dispatchEvent(new Event('focusin'));
    fixture.detectChanges();
    expect(fixture.debugElement.queryAll(By.css('.mat-option')).length).toBe(3);
    expect(fixture.debugElement.queryAll(By.css('.mat-option'))[0]
               .nativeElement.textContent)
        .toContain('label1');
  });

  it('setFormState sets form values using ForemanRuleSet input', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    fixture.componentInstance.setFormState({
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ANY,  // NOT Default
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: true, osLinux: true, osDarwin: false},
        },
        {
          ruleType: ForemanClientRuleType.LABEL,
          label: {
            labelNames: ['foo', 'bar'],
            matchMode: ForemanLabelClientRuleMatchMode.MATCH_ANY
          },
        },
        {
          ruleType: ForemanClientRuleType.INTEGER,
          integer: {
            operator: ForemanIntegerClientRuleOperator.GREATER_THAN,
            value: '123',
            field: ForemanIntegerClientRuleForemanIntegerField.CLIENT_CLOCK
          },
        },
        {
          ruleType: ForemanClientRuleType.REGEX,
          regex: {
            attributeRegex: 'I am a regex',
            field: ForemanRegexClientRuleForemanStringField.CLIENT_DESCRIPTION
          },
        },
      ]
    });

    // OS form values
    expect(await getCheckboxValue(fixture, '[id=condition_0_windows]'))
        .toBe(true);
    expect(await getCheckboxValue(fixture, '[id=condition_0_linux]'))
        .toBe(true);
    expect(await getCheckboxValue(fixture, '[id=condition_0_darwin]'))
        .toBe(false);

    // Labels form values
    expect(await getSelectBoxValue(fixture, '[id=condition_1_match_mode]'))
        .toBe('Match any');
    expect(await getInputValue(fixture, '[id=condition_1_label_name_0]'))
        .toBe('foo');
    expect(await getInputValue(fixture, '[id=condition_1_label_name_1]'))
        .toBe('bar');

    // Client Clock form values
    expect(await getSelectBoxValue(fixture, '[id=condition_2_operator]'))
        .toBe('Greater Than');
    expect(await getInputValue(fixture, '[id=condition_2_integer_value]'))
        .toBe('123');

    // Client Description form values
    expect(await getInputValue(fixture, '[id=condition_3_regex_value]'))
        .toBe('I am a regex');
  });
});
