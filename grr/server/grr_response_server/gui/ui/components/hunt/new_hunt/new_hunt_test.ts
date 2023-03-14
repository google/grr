import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {Component} from '@angular/core';
import {ComponentFixture, fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatButtonToggleHarness} from '@angular/material/button-toggle/testing';
import {MatCheckboxHarness} from '@angular/material/checkbox/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatSelectHarness} from '@angular/material/select/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ForemanClientRuleSetMatchMode, ForemanClientRuleType, ForemanIntegerClientRuleForemanIntegerField, ForemanIntegerClientRuleOperator, ForemanLabelClientRuleMatchMode, ForemanRegexClientRuleForemanStringField} from '../../../lib/api/api_interfaces';
import {RequestStatusType} from '../../../lib/api/track_request';
import {newFlow, newHunt, newSafetyLimits} from '../../../lib/models/model_test_util';
import {ApprovalCardLocalStore} from '../../../store/approval_card_local_store';
import {ApprovalCardLocalStoreMock, mockApprovalCardLocalStore} from '../../../store/approval_card_local_store_test_util';
import {ConfigGlobalStore} from '../../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../../store/config_global_store_test_util';
import {HuntApprovalGlobalStore} from '../../../store/hunt_approval_global_store';
import {NewHuntLocalStore} from '../../../store/new_hunt_local_store';
import {mockNewHuntLocalStore} from '../../../store/new_hunt_local_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {UserGlobalStore} from '../../../store/user_global_store';
import {getActivatedChildRoute, initTestEnvironment} from '../../../testing';

import {NewHuntModule} from './module';
import {NewHunt} from './new_hunt';


// TODO: Refactor form helpers into common `form_testing.ts` file.
// For unknown reasons (likely related to some injection) we cannot use the
// following helper functions which are also defined in `form_testing.ts`. Thus,
// we copy them over here to be able to easily check the component values.
async function getCheckboxValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<boolean> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const checkboxHarness = await harnessLoader.getHarness(
      MatCheckboxHarness.with({selector: query}));
  return await checkboxHarness.isChecked();
}

async function getSelectBoxValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<string> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const selectionBoxHarness =
      await harnessLoader.getHarness(MatSelectHarness.with({selector: query}));
  return await selectionBoxHarness.getValueText();
}

async function getInputValue(
    fixture: ComponentFixture<unknown>, query: string): Promise<string> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const inputHarness =
      await harnessLoader.getHarness(MatInputHarness.with({selector: query}));
  return await inputHarness.getValue();
}

async function isButtonToggleSelected(
    fixture: ComponentFixture<unknown>, query: string,
    text: string): Promise<boolean> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const toggle = await harnessLoader.getHarness(
      MatButtonToggleHarness.with({selector: query, text}));
  return await toggle.isChecked();
}

initTestEnvironment();

@Component({template: ''})
class TestComponent {
}

describe('new hunt test', () => {
  let configGlobalStore: ConfigGlobalStoreMock;
  let approvalCardLocalStore: ApprovalCardLocalStoreMock;

  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();
    approvalCardLocalStore = mockApprovalCardLocalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            NewHuntModule,
            RouterTestingModule.withRoutes([
              {path: 'new-hunt', component: NewHunt},
              {path: 'hunts/:id', component: TestComponent}
            ]),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
            {
              provide: ConfigGlobalStore,
              useFactory: () => configGlobalStore,
            },
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            NewHuntLocalStore, {useFactory: mockNewHuntLocalStore})
        .overrideProvider(
            ApprovalCardLocalStore, {useFactory: () => approvalCardLocalStore})
        .compileComponents();
  }));

  it('starts with editable title', async () => {
    await TestBed.inject(Router).navigate(
        ['new-hunt'], {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});
    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();

    const editButton = fixture.debugElement.query(By.css('button[name=edit]'));
    expect(editButton).toBeFalsy();

    const title = fixture.debugElement.query(By.css('h1'));
    expect(title.attributes['contenteditable']).not.toBeFalse();
  });

  it('loads and displays original Flow', async () => {
    await TestBed.inject(Router).navigate(
        ['new-hunt'], {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});
    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();
    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    newHuntLocalStore.mockedObservables.flowWithDescriptor$.next({
      flow: newFlow({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      descriptor: {
        name: 'KeepAlive',
        friendlyName: 'KeepAlive',
        category: 'a',
        defaultArgs: {},
      },
      flowArgType: 'someType',
    });
    fixture.detectChanges();

    const flowSection =
        fixture.debugElement.query(By.css('.new-hunt-container'))
            .query(By.css('.config'));
    const text = flowSection.nativeElement.textContent;
    expect(text).toContain('morty');
    expect(text).toContain('KeepAlive');
  });

  it('displays flow from original hunt', async () => {
    await TestBed.inject(Router).navigate(
        ['new-hunt'], {queryParams: {'huntId': 'H1234'}});
    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();
    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    newHuntLocalStore.mockedObservables.originalHunt$.next(newHunt({
      huntId: 'H1234',
      flowName: 'KeepAlive',
    }));
    fixture.detectChanges();

    const flowSection =
        fixture.debugElement.query(By.css('.new-hunt-container'))
            .query(By.css('.config'));
    const text = flowSection.nativeElement.textContent;
    expect(text).toContain('Flow arguments');
    expect(text).toContain('KeepAlive');
  });

  it('loads and displays hunt params', async () => {
    await TestBed.inject(Router).navigate(
        ['new-hunt'], {queryParams: {'huntId': 'H1234'}});

    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();

    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    expect(newHuntLocalStore.selectOriginalHunt).toHaveBeenCalledWith('H1234');

    newHuntLocalStore.mockedObservables.originalHunt$.next(newHunt({
      huntId: 'H1234',
      description: 'A hunt',
      clientRuleSet: {
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
      },
      safetyLimits: newSafetyLimits({
        clientRate: 0,
        clientLimit: BigInt(2022),
        expiryTime: BigInt(3600),
      }),
      outputPlugins: [{
        pluginName: 'BigQueryOutputPlugin',
        args: {'exportOptions': {annotations: ['lalala', 'lelele']}},
      }],
    }));
    newHuntLocalStore.mockedObservables.huntId$.next('H1234');
    fixture.detectChanges();

    // Check title was copied.
    const huntTitle = fixture.debugElement.query(By.css('title-editor'));
    expect(huntTitle.nativeElement.textContent).toContain('A hunt (copy)');

    const referencesSection = fixture.debugElement.query(By.css('table'));
    expect(referencesSection.nativeElement.textContent)
        .toContain('Based on fleet collection');
    expect(referencesSection.query(By.css('a')).nativeElement.textContent)
        .toContain('H1234');

    // Check clientsForm values were set.
    expect(await getCheckboxValue(fixture, '[id=condition_0_windows]'))
        .toBe(true);
    expect(await getCheckboxValue(fixture, '[id=condition_0_linux]'))
        .toBe(true);
    expect(await getCheckboxValue(fixture, '[id=condition_0_darwin]'))
        .toBe(false);
    expect(await getSelectBoxValue(fixture, '[id=condition_1_match_mode]'))
        .toBe('Match any');
    expect(await getInputValue(fixture, '[id=condition_1_label_name_0]'))
        .toBe('foo');
    expect(await getInputValue(fixture, '[id=condition_1_label_name_1]'))
        .toBe('bar');
    expect(await getSelectBoxValue(fixture, '[id=condition_2_operator]'))
        .toBe('Greater Than');
    expect(await getInputValue(fixture, '[id=condition_2_integer_value]'))
        .toBe('123');
    expect(await getInputValue(fixture, '[id=condition_3_regex_value]'))
        .toBe('I am a regex');

    // Check paramForm values were set.
    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Unlimited'))
        .toBe(true);
    expect(await isButtonToggleSelected(fixture, '.run-on-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=customClientLimit]'))
        .toBe('2022');
    expect(await getInputValue(fixture, '[name=activeFor]')).toBe('1 h');

    // Open output plugins section before checking.
    const expandButton =
        fixture.debugElement.query(By.css('#output-plugins-form-toggle'));
    expandButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    // Check outputPluginsForm values were set.
    expect(await getInputValue(fixture, '#plugin_0_annotation_0'))
        .toEqual('lalala');
    expect(await getInputValue(fixture, '#plugin_0_annotation_1'))
        .toEqual('lelele');
  });

  it('displays errors if no flow or hunt are selected', async () => {
    await TestBed.inject(Router).navigate(
        ['new-hunt'], {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});

    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();

    const chip = fixture.debugElement.query(By.css('mat-chip'));
    expect(chip).toBeTruthy();
    expect(chip.nativeElement.textContent).toContain('MUST');

    const button = fixture.debugElement.query(By.css('#runHunt'));
    expect(button.attributes['disabled']).toBe('true');

    const error = fixture.debugElement.query(By.css('mat-error'));
    expect(error).toBeTruthy();
    expect(error.nativeElement.textContent).toContain('must use an existing');
  });

  it('does NOT display chip if flow is selected', async () => {
    await TestBed.inject(Router).navigate(
        ['new-hunt'], {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});

    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();
    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    newHuntLocalStore.mockedObservables.flowWithDescriptor$.next({
      flow: newFlow({
        name: 'KeepAlive',
        creator: 'morty',
      }),
      descriptor: {
        name: 'KeepAlive',
        friendlyName: 'KeepAlive',
        category: 'a',
        defaultArgs: {},
      },
      flowArgType: 'someType',
    });
    newHuntLocalStore.mockedObservables.originalHunt$.next(null);
    fixture.detectChanges();

    const chip = fixture.debugElement.query(By.css('mat-chip'));
    expect(chip).toBeFalsy();
    expect(fixture.nativeElement.textContent).not.toContain('MUST');

    const button = fixture.debugElement.query(By.css('#runHunt'));
    expect(button.attributes['disabled']).toBeFalsy();
  });

  it('does NOT display chip if hunt is selected', async () => {
    await TestBed.inject(Router).navigate(
        ['new-hunt'], {queryParams: {'huntId': 'H1234'}});

    const fixture = TestBed.createComponent(NewHunt);
    fixture.detectChanges();
    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    newHuntLocalStore.mockedObservables.originalHunt$.next(newHunt({
      huntId: 'H1234',
      flowName: 'KeepAlive',
    }));
    newHuntLocalStore.mockedObservables.flowWithDescriptor$.next(null);
    fixture.detectChanges();

    const chip = fixture.debugElement.query(By.css('mat-chip'));
    expect(chip).toBeFalsy();
    expect(fixture.nativeElement.textContent).not.toContain('MUST');

    const button = fixture.debugElement.query(By.css('#runHunt'));
    expect(button.attributes['disabled']).toBeFalsy();
  });

  it('sends request approval when child approval component emits the info',
     async () => {
       await TestBed.inject(Router).navigate(
           ['new-hunt'],
           {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});
       const fixture = TestBed.createComponent(NewHunt);
       const loader = TestbedHarnessEnvironment.loader(fixture);
       fixture.detectChanges();
       const newHuntLocalStore =
           injectMockStore(NewHuntLocalStore, fixture.debugElement);
       const huntApprovalGlobalStore = injectMockStore(HuntApprovalGlobalStore);
       fixture.detectChanges();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: true,
       });
       fixture.detectChanges();

       configGlobalStore.mockedObservables.approvalConfig$.next(
           {optionalCcEmail: 'foo@example.org'});
       fixture.detectChanges();

       const approversInput =
           fixture.debugElement.query(By.css('mat-chip-list input'));
       approversInput.triggerEventHandler('focusin', null);
       fixture.detectChanges();

       approvalCardLocalStore.mockedObservables.approverSuggestions$.next(
           ['user@gmail.com']);
       fixture.detectChanges();

       const input = await loader.getHarness(MatAutocompleteHarness);
       await input.enterText('user');
       const options = await input.getOptions();
       await options[0].click();
       fixture.detectChanges();

       const reason = await loader.getHarness(
           MatInputHarness.with({selector: '[name=reason]'}));
       await reason.setValue('sample reason');
       fixture.detectChanges();
       const button = fixture.debugElement.query(By.css('#runHunt'));
       button.triggerEventHandler('click', new MouseEvent('click'));

       fixture.detectChanges();
       expect(newHuntLocalStore.runHunt).toHaveBeenCalled();

       newHuntLocalStore.mockedObservables.huntId$.next('h1234');
       fixture.detectChanges();

       expect(huntApprovalGlobalStore.requestHuntApproval)
           .toHaveBeenCalledWith({
             huntId: 'h1234',
             approvers: ['user@gmail.com'],
             reason: 'sample reason',
             cc: ['foo@example.org'],
           });
     });

  it('changes the route when finishes sending request', fakeAsync(async () => {
       await TestBed.inject(Router).navigate(
           ['new-hunt'],
           {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});
       const fixture = TestBed.createComponent(NewHunt);
       fixture.detectChanges();
       const newHuntLocalStore =
           injectMockStore(NewHuntLocalStore, fixture.debugElement);
       fixture.detectChanges();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: true,
       });

       newHuntLocalStore.mockedObservables.huntId$.next('h1234');
       fixture.detectChanges();
       injectMockStore(HuntApprovalGlobalStore, fixture.debugElement)
           .mockedObservables.requestApprovalStatus$.next(
               {status: RequestStatusType.SENT});
       fixture.detectChanges();
       tick();

       const location = TestBed.inject(Location);
       expect(location.path()).toEqual('/hunts/h1234');
     }));

  it('changes the route when finishes sending request when hunt approval is not required',
     fakeAsync(async () => {
       await TestBed.inject(Router).navigate(
           ['new-hunt'],
           {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});
       const fixture = TestBed.createComponent(NewHunt);
       fixture.detectChanges();
       const newHuntLocalStore =
           injectMockStore(NewHuntLocalStore, fixture.debugElement);
       fixture.detectChanges();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: false,
       });

       newHuntLocalStore.mockedObservables.huntId$.next('h1234');
       fixture.detectChanges();
       tick();

       const location = TestBed.inject(Location);
       expect(location.path()).toEqual('/hunts/h1234');
     }));

  it('does not show approval form when is not needed', fakeAsync(async () => {
       await TestBed.inject(Router).navigate(
           ['new-hunt'],
           {queryParams: {'flowId': 'F1234', 'clientId': 'C1234'}});
       const fixture = TestBed.createComponent(NewHunt);
       fixture.detectChanges();
       tick();

       injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
         name: 'approver',
         canaryMode: false,
         huntApprovalRequired: false,
       });
       fixture.detectChanges();

       expect(fixture.componentInstance.approvalCard).toBe(undefined);
     }));
});
