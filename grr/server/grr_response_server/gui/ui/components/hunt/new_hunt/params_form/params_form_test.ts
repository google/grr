import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatButtonToggleHarness} from '@angular/material/button-toggle/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {NewHuntLocalStore} from '../../../../store/new_hunt_local_store';
import {mockNewHuntLocalStore} from '../../../../store/new_hunt_local_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../../store/store_test_providers';
import {initTestEnvironment} from '../../../../testing';

import {ParamsFormModule} from './module';
import {ParamsForm} from './params_form';

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

async function selectButton(
    fixture: ComponentFixture<unknown>, query: string, text: string) {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const toggle = await harnessLoader.getHarness(
      MatButtonToggleHarness.with({selector: query, text}));
  await toggle.check();
}

async function isButtonSelected(
    fixture: ComponentFixture<unknown>, query: string,
    text: string): Promise<boolean> {
  const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
  const toggle = await harnessLoader.getHarness(
      MatButtonToggleHarness.with({selector: query, text}));
  return await toggle.isChecked();
}

describe('params form test', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ParamsFormModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            NewHuntLocalStore, {useFactory: mockNewHuntLocalStore})
        .compileComponents();
  }));

  it('toggles contents on click on toggle button', () => {
    const fixture = TestBed.createComponent(ParamsForm);
    const button = fixture.debugElement.query(By.css('#param-form-toggle'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('only renders the advanced params when clicking show safety limit', () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();

    const button = fixture.debugElement.query(By.css('#toggle-advance-params'));
    expect(button.nativeElement.textContent)
        .toContain('expand_more Show safety limits ');
    const element =
        fixture.debugElement.query(By.css('.advanced-params')).nativeElement;
    expect(getComputedStyle(element).display).toEqual('none');

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(button.nativeElement.textContent)
        .toContain('expand_less Hide safety limits ');
    expect(getComputedStyle(element).display).not.toEqual('none');
  });

  it('only set the default values of the parameters', async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();
    const newHuntLocalStore =
        injectMockStore(NewHuntLocalStore, fixture.debugElement);
    newHuntLocalStore.mockedObservables.safetyLimits$.next({
      clientRate: 200.0,
      clientLimit: BigInt(123),
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(1000),
      avgCpuSecondsPerClientLimit: BigInt(60),
      avgNetworkBytesPerClientLimit: BigInt(10485760),
      cpuLimit: BigInt(0),
      expiryTime: BigInt(1209600),
      networkBytesLimit: BigInt(0),
    });
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component.form.controls['clientRate'].value).toBe(200.0);
    expect(component.form.controls['expiryTime'].value).toBe(BigInt(1209600));
    expect(component.form.controls['crashLimit'].value).toBe(BigInt(100));
    expect(component.form.controls['avgResultsPerClientLimit'].value)
        .toBe(BigInt(1000));
    expect(component.form.controls['avgCpuSecondsPerClientLimit'].value)
        .toBe(BigInt(60));
    expect(component.form.controls['avgNetworkBytesPerClientLimit'].value)
        .toBe(BigInt(10485760));
  });


  it('only renders custom input when select custom', async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    const loader = TestbedHarnessEnvironment.loader(fixture);
    fixture.detectChanges();
    const clientRate = await loader.getAllHarnesses(
        MatInputHarness.with({selector: '[name=customClientLimit]'}));
    expect(clientRate.length).toBe(0);
    const customClientRateButton = fixture.debugElement.query(By.css('.run-on'))
                                       .children[2]
                                       .query(By.css('button'));
    customClientRateButton.triggerEventHandler(
        'click', new MouseEvent('click'));
    fixture.detectChanges();
    const newClientRate = await loader.getAllHarnesses(
        MatInputHarness.with({selector: '[name=customClientLimit]'}));
    expect(newClientRate.length).toBe(1);
  });

  it('buildSafetyLimits builds SafetyLimits using the form values',
     async () => {
       const fixture = TestBed.createComponent(ParamsForm);
       fixture.detectChanges();

       await selectButton(fixture, '.rollout-speed-option', 'Unlimited');
       await selectButton(fixture, '.run-on-option', 'Custom');
       fixture.detectChanges();
       await setInputValue(fixture, '[name=customClientLimit]', '2022');
       await setInputValue(fixture, '[name=activeFor]', '1 h');

       const toggleAdvancedButton =
           fixture.debugElement.query(By.css('#toggle-advance-params'));
       toggleAdvancedButton.triggerEventHandler(
           'click', new MouseEvent('click'));
       fixture.detectChanges();

       await setInputValue(fixture, '[name=crashLimit]', '12');
       await setInputValue(fixture, '[name=aveResults]', '34');
       await setInputValue(fixture, '[name=aveCPU]', '56');
       await setInputValue(fixture, '[name=aveNetwork]', '78');
       await setInputValue(fixture, '[name=cpuLimit]', '90');
       await setInputValue(fixture, '[name=networkLimit]', '13');

       expect(fixture.componentInstance.buildSafetyLimits()).toEqual({
         clientRate: 0,
         clientLimit: BigInt(2022),
         expiryTime: BigInt(3600),
         crashLimit: BigInt(12),
         avgResultsPerClientLimit: BigInt(34),
         avgCpuSecondsPerClientLimit: BigInt(56),
         avgNetworkBytesPerClientLimit: BigInt(78),
         cpuLimit: BigInt(90),
         networkBytesLimit: BigInt(13),
       });
     });

  it('setFormState sets form values using SafetyLimits', async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();

    fixture.componentInstance.setFormState({
      clientRate: 0,
      clientLimit: BigInt(2022),
      expiryTime: BigInt(3600),
      crashLimit: BigInt(12),
      avgResultsPerClientLimit: BigInt(34),
      avgCpuSecondsPerClientLimit: BigInt(56),
      avgNetworkBytesPerClientLimit: BigInt(78),
      cpuLimit: BigInt(90),
      networkBytesLimit: BigInt(13),
    });

    expect(
        await isButtonSelected(fixture, '.rollout-speed-option', 'Unlimited'))
        .toBe(true);
    expect(await isButtonSelected(fixture, '.run-on-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=customClientLimit]'))
        .toBe('2022');
    expect(await getInputValue(fixture, '[name=activeFor]')).toBe('1 h');

    const toggleAdvancedButton =
        fixture.debugElement.query(By.css('#toggle-advance-params'));
    toggleAdvancedButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(await getInputValue(fixture, '[name=crashLimit]')).toBe('12');
    expect(await getInputValue(fixture, '[name=aveResults]')).toBe('34');
    expect(await getInputValue(fixture, '[name=aveCPU]')).toBe('56 s');
    expect(await getInputValue(fixture, '[name=aveNetwork]')).toBe('78 B');
    expect(await getInputValue(fixture, '[name=cpuLimit]')).toBe('90 s');
    expect(await getInputValue(fixture, '[name=networkLimit]')).toBe('13 B');
  });
});
