import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed} from '@angular/core/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {getInputValue, isButtonToggleSelected, selectButtonToggle, setInputValue} from '../../../form_testing';
import {initTestEnvironment} from '../../../testing';

import {RolloutFormModule} from './module';
import {RolloutForm} from './rollout_form';


initTestEnvironment();

describe('RolloutForm Component', () => {
  beforeEach(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            RolloutFormModule,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  });

  it('starts with the default values', async () => {
    const fixture = TestBed.createComponent(RolloutForm);
    fixture.detectChanges();

    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Standard'))
        .toBe(true);
    expect(await isButtonToggleSelected(
               fixture, '.run-on-option', 'Small client sample'))
        .toBe(true);
  });

  it('only renders custom input when select custom', async () => {
    const fixture = TestBed.createComponent(RolloutForm);
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

  it('setFormState sets form values using SafetyLimits', async () => {
    const fixture = TestBed.createComponent(RolloutForm);
    fixture.detectChanges();
    fixture.detectChanges();

    fixture.componentInstance.setFormState({
      clientRate: 0,
      clientLimit: BigInt(2023),
      expiryTime: BigInt(3600),
      crashLimit: BigInt(12),
      avgResultsPerClientLimit: BigInt(34),
      avgCpuSecondsPerClientLimit: BigInt(56),
      avgNetworkBytesPerClientLimit: BigInt(78),
      perClientCpuLimit: BigInt(90),
      perClientNetworkBytesLimit: BigInt(13),
    });

    expect(await isButtonToggleSelected(
               fixture, '.rollout-speed-option', 'Unlimited'))
        .toBe(true);
    expect(fixture.debugElement.query(By.css('[name=clientRate]'))).toBeFalsy();
    expect(await isButtonToggleSelected(fixture, '.run-on-option', 'Custom'))
        .toBe(true);
    expect(await getInputValue(fixture, '[name=customClientLimit]'))
        .toBe('2023');
  });

  describe('updates param help according to input', () => {
    it('run on', async () => {
      const fixture = TestBed.createComponent(RolloutForm);
      fixture.detectChanges();

      await selectButtonToggle(
          fixture, '.run-on-option', 'All matching clients');
      const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
      const harness = await harnessLoader.getHarness(
          MatTooltipHarness.with({selector: '[name=runOnHelp]'}));
      await harness.show();
      expect(await harness.getTooltipText())
          .toContain('as many clients as possible');

      await selectButtonToggle(
          fixture, '.run-on-option', 'Small client sample');
      await harness.show();
      expect(await harness.getTooltipText()).toContain('100 clients');

      await selectButtonToggle(fixture, '.run-on-option', 'Custom');
      await setInputValue(fixture, '[name=customClientLimit]', '42');
      await harness.show();
      expect(await harness.getTooltipText()).toContain('42 clients');
    });

    it('rollout speed', async () => {
      const fixture = TestBed.createComponent(RolloutForm);
      fixture.detectChanges();

      await selectButtonToggle(fixture, '.rollout-speed-option', 'Unlimited');
      const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
      const harness = await harnessLoader.getHarness(
          MatTooltipHarness.with({selector: '[name=rolloutSpeedHelp]'}));
      await harness.show();
      expect(await harness.getTooltipText())
          .toContain('as many clients as possible');

      await selectButtonToggle(fixture, '.rollout-speed-option', 'Standard');
      await harness.show();
      expect(await harness.getTooltipText()).toContain('200 clients');

      await selectButtonToggle(fixture, '.rollout-speed-option', 'Custom');
      await setInputValue(fixture, '[name=clientRate]', '42');
      await harness.show();
      expect(await harness.getTooltipText()).toContain('42 clients');
    });
  });
});
