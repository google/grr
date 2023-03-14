import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed} from '@angular/core/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {getInputValue, isButtonToggleSelected} from '../../../form_testing';
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
      cpuLimit: BigInt(90),
      networkBytesLimit: BigInt(13),
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
});
