import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  getHintValues,
  getInputValue,
  isButtonToggleSelected,
  selectButtonToggle,
  setInputValue,
} from '../../../../form_testing';
import {NewHuntLocalStore} from '../../../../store/new_hunt_local_store';
import {mockNewHuntLocalStore} from '../../../../store/new_hunt_local_store_test_util';
import {
  injectMockStore,
  STORE_PROVIDERS,
} from '../../../../store/store_test_providers';
import {initTestEnvironment} from '../../../../testing';

import {ParamsFormModule} from './module';
import {ParamsForm} from './params_form';

initTestEnvironment();

describe('params form test', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, ParamsFormModule],
      providers: [...STORE_PROVIDERS],
      teardown: {destroyAfterEach: false},
    })
      .overrideProvider(NewHuntLocalStore, {useFactory: mockNewHuntLocalStore})
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

    const buttonTop = fixture.debugElement.query(
      By.css('[name=toggle-advance-params-top]'),
    );
    expect(buttonTop.nativeElement.textContent).toContain(
      'expand_more Show safety limits ',
    );
    const element = fixture.debugElement.query(
      By.css('.advanced-params'),
    ).nativeElement;
    expect(getComputedStyle(element).display).toEqual('none');

    const buttonBottom = fixture.debugElement.query(
      By.css('[name=toggle-advance-params-bottom]'),
    );
    buttonBottom.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(buttonBottom.nativeElement.textContent).toContain(
      'expand_less Hide safety limits ',
    );
    expect(getComputedStyle(element).display).not.toEqual('none');
  });

  it('only set the default values of the parameters', async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();
    const newHuntLocalStore = injectMockStore(
      NewHuntLocalStore,
      fixture.debugElement,
    );
    newHuntLocalStore.mockedObservables.defaultSafetyLimits$.next({
      clientRate: 200.0,
      clientLimit: BigInt(123),
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(1000),
      avgCpuSecondsPerClientLimit: BigInt(60),
      avgNetworkBytesPerClientLimit: BigInt(10485760),
      perClientCpuLimit: BigInt(0),
      perClientNetworkBytesLimit: BigInt(0),
      expiryTime: BigInt(1209600),
    });
    fixture.detectChanges();
    const component = fixture.componentInstance;
    expect(component.form.controls['expiryTime'].value).toBe(BigInt(1209600));
    expect(component.form.controls['crashLimit'].value).toBe(BigInt(100));
    expect(component.form.controls['avgResultsPerClientLimit'].value).toBe(
      BigInt(1000),
    );
    expect(component.form.controls['avgCpuSecondsPerClientLimit'].value).toBe(
      BigInt(60),
    );
    expect(component.form.controls['avgNetworkBytesPerClientLimit'].value).toBe(
      BigInt(10485760),
    );
  });

  it('buildSafetyLimits builds SafetyLimits using the form values', async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();

    await selectButtonToggle(fixture, '.rollout-speed-option', 'Unlimited');
    await selectButtonToggle(fixture, '.run-on-option', 'Custom');
    fixture.detectChanges();
    await setInputValue(fixture, '[name=customClientLimit]', '2022');
    await setInputValue(fixture, '[name=activeFor]', '1 h');

    const toggleAdvancedButton = fixture.debugElement.query(
      By.css('[name=toggle-advance-params-top]'),
    );
    toggleAdvancedButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    await setInputValue(fixture, '[name=crashLimit]', '12');
    await setInputValue(fixture, '[name=aveResults]', '34');
    await setInputValue(fixture, '[name=aveCPU]', '56');
    await setInputValue(fixture, '[name=aveNetwork]', '78');
    await selectButtonToggle(fixture, '.client-cpu-limit-option', 'Custom');
    await setInputValue(fixture, '[name=perClientCpuLimit]', '90');
    await selectButtonToggle(
      fixture,
      '.client-network-limit-option',
      'Unlimited',
    );

    expect(fixture.componentInstance.buildSafetyLimits()).toEqual({
      clientRate: 0,
      clientLimit: BigInt(2022),
      expiryTime: BigInt(3600),
      crashLimit: BigInt(12),
      avgResultsPerClientLimit: BigInt(34),
      avgCpuSecondsPerClientLimit: BigInt(56),
      avgNetworkBytesPerClientLimit: BigInt(78),
      perClientCpuLimit: BigInt(90),
      perClientNetworkBytesLimit: BigInt(0),
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
      perClientCpuLimit: BigInt(90),
      perClientNetworkBytesLimit: BigInt(0),
    });

    expect(
      await isButtonToggleSelected(
        fixture,
        '.rollout-speed-option',
        'Unlimited',
      ),
    ).toBe(true);
    expect(
      await isButtonToggleSelected(fixture, '.run-on-option', 'Custom'),
    ).toBe(true);
    expect(await getInputValue(fixture, '[name=customClientLimit]')).toBe(
      '2022',
    );
    expect(await getInputValue(fixture, '[name=activeFor]')).toBe('1 h');

    const toggleAdvancedButton = fixture.debugElement.query(
      By.css('[name=toggle-advance-params-top]'),
    );
    toggleAdvancedButton.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();

    expect(await getInputValue(fixture, '[name=crashLimit]')).toBe('12');
    expect(await getInputValue(fixture, '[name=aveResults]')).toBe('34');
    expect(await getInputValue(fixture, '[name=aveCPU]')).toBe('56 s');
    expect(await getInputValue(fixture, '[name=aveNetwork]')).toBe('78 B');
    expect(
      await isButtonToggleSelected(
        fixture,
        '.rollout-speed-option',
        'Unlimited',
      ),
    ).toBe(true);
    expect(
      await isButtonToggleSelected(
        fixture,
        '.client-cpu-limit-option',
        'Custom',
      ),
    ).toBe(true);
    expect(await getInputValue(fixture, '[name=perClientCpuLimit]')).toBe(
      '90 s',
    );
    expect(
      await isButtonToggleSelected(
        fixture,
        '.client-network-limit-option',
        'Unlimited',
      ),
    ).toBe(true);
  });

  it('form validation shows hints for invalid input', fakeAsync(async () => {
    const fixture = TestBed.createComponent(ParamsForm);
    fixture.detectChanges();

    // Expiration time
    await setInputValue(fixture, '[name=activeFor]', '0');
    tick();
    expect(await getHintValues(fixture, '[name=expiryTimeFormField]')).toEqual([
      'Value "0" is not allowed',
    ]);

    await setInputValue(fixture, '[name=activeFor]', 'argh');
    tick();
    expect(await getHintValues(fixture, '[name=expiryTimeFormField]')).toEqual([
      'Invalid input',
    ]);

    // Average CPU time per client
    await setInputValue(fixture, '[name=aveCPU]', 'argh');
    tick();
    expect(await getHintValues(fixture, '[name=aveCPUFormField]')).toEqual([
      'Invalid input',
    ]);
    await setInputValue(fixture, '[name=aveCPU]', '0');
    tick();
    expect(await getHintValues(fixture, '[name=aveCPUFormField]')).toEqual([
      'Value "0" is not allowed',
    ]);

    // CPU time limit per client
    expect(
      await isButtonToggleSelected(
        fixture,
        '.client-cpu-limit-option',
        'Unlimited',
      ),
    ).toBe(true);
    await selectButtonToggle(fixture, '.client-cpu-limit-option', 'Custom');
    await setInputValue(fixture, '[name=perClientCpuLimit]', 'argh');
    tick();
    expect(
      await getHintValues(fixture, '[name=perClientCPULimitFormField]'),
    ).toEqual(['Invalid input']);
    await setInputValue(fixture, '[name=perClientCpuLimit]', '0');
    tick();
    expect(
      await getHintValues(fixture, '[name=perClientCPULimitFormField]'),
    ).toEqual(['Value "0" is not allowed']);

    // Average network usage per client
    await setInputValue(fixture, '[name=aveNetwork]', 'argh');
    tick();
    expect(await getHintValues(fixture, '[name=aveNetworkFormField]')).toEqual([
      'Invalid input',
    ]);
    await setInputValue(fixture, '[name=aveNetwork]', '0');
    tick();
    expect(await getHintValues(fixture, '[name=aveNetworkFormField]')).toEqual([
      'Value must be larger than "0"',
    ]);

    // Network bytes limit per client
    expect(
      await isButtonToggleSelected(
        fixture,
        '.client-network-limit-option',
        'Unlimited',
      ),
    ).toBe(true);
    await selectButtonToggle(fixture, '.client-network-limit-option', 'Custom');
    await setInputValue(fixture, '[name=perClientNetworkBytesLimit]', 'argh');
    tick();
    expect(
      await getHintValues(
        fixture,
        '[name=perClientNetworkBytesLimitFormField]',
      ),
    ).toEqual(['Invalid input']);
    await setInputValue(fixture, '[name=perClientNetworkBytesLimit]', '0');
    tick();
    expect(
      await getHintValues(
        fixture,
        '[name=perClientNetworkBytesLimitFormField]',
      ),
    ).toEqual(['Value must be larger than "0"']);
  }));
});
