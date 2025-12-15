import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {SafetyLimits} from '../../../lib/models/hunt';
import {newSafetyLimits} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';
import {RolloutForm} from './rollout_form';
import {RolloutFormHarness} from './testing/rollout_form_harness';

initTestEnvironment();

async function createComponent(initialSafetyLimits?: SafetyLimits) {
  const fixture = TestBed.createComponent(RolloutForm);
  if (!initialSafetyLimits) {
    initialSafetyLimits = newSafetyLimits({});
  }
  fixture.componentRef.setInput('initialSafetyLimits', initialSafetyLimits);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    RolloutFormHarness,
  );

  return {fixture, harness};
}

describe('Rollout Form Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [RolloutForm, NoopAnimationsModule],
    }).compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('is initialized with the provided values', async () => {
    const {harness} = await createComponent({
      clientRate: 500,
      clientLimit: BigInt(123),
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(1000),
      avgCpuSecondsPerClientLimit: BigInt(60),
      avgNetworkBytesPerClientLimit: BigInt(10000000),
      perClientCpuLimit: BigInt(10),
      perClientNetworkBytesLimit: BigInt(20),
      expiryTime: BigInt(1209600),
    });
    const safetyLimits = await harness.collapsibleContainer();
    await safetyLimits.expand();

    const rolloutSpeedToggleGroup = await harness.rolloutSpeedToggleGroup();
    const customRolloutToggle = (
      await rolloutSpeedToggleGroup.getToggles({
        text: 'Custom',
      })
    )[0];
    expect(await customRolloutToggle.isChecked()).toBeTrue();
    const rolloutSpeedInput = await harness.getRolloutSpeedInput();
    expect(await rolloutSpeedInput.getValue()).toBe('500');

    const runOnButtonToggleGroup = await harness.clientLimitToggleGroup();
    const customClientLimitToggle = (
      await runOnButtonToggleGroup.getToggles({
        text: 'Custom',
      })
    )[0];
    expect(await customClientLimitToggle.isChecked()).toBeTrue();
    const clientLimitInput = await harness.getClientLimitInput();
    expect(await clientLimitInput.getValue()).toBe('123');

    const expirationTimeInput = await harness.getExpiryTimeInput();
    expect(await expirationTimeInput.getValue()).toBe('2 w');

    const crashLimitInput = await harness.getCrashLimitInput();
    expect(await crashLimitInput.getValue()).toBe('100');

    const avgResultsPerClientLimitInput =
      await harness.getAvgResultsPerClientLimitInput();
    expect(await avgResultsPerClientLimitInput.getValue()).toBe('1000');

    const avgCpuSecondsPerClientLimitInput =
      await harness.getAvgCpuSecondsPerClientLimitInput();
    expect(await avgCpuSecondsPerClientLimitInput.getValue()).toBe('1 m');

    const avgNetworkBytesPerClientLimitInput =
      await harness.getAvgNetworkBytesPerClientLimitInput();
    expect(await avgNetworkBytesPerClientLimitInput.getValue()).toBe('10 MB');

    const perClientCpuLimitInput = await harness.getPerClientCpuLimitInput();
    expect(await perClientCpuLimitInput.getValue()).toBe('10 s');

    const perClientNetworkBytesLimitInput =
      await harness.getPerClientNetworkBytesLimitInput();
    expect(await perClientNetworkBytesLimitInput.getValue()).toBe('20 B');
  });

  it('hides safety limits by default', async () => {
    const {harness} = await createComponent();

    const collapsibleContainer = await harness.collapsibleContainer();
    expect(await collapsibleContainer.isContentVisible()).toBeFalse();
    expect(await harness.crashLimitFormField()).toBeNull();
    expect(await harness.avgResultsPerClientLimitFormField()).toBeNull();
    expect(await harness.avgCpuSecondsPerClientLimitFormField()).toBeNull();
    expect(await harness.avgNetworkBytesPerClientLimitFormField()).toBeNull();
    expect(await harness.cpuTimeLimitToggleGroup()).toBeNull();
    expect(await harness.networkBytesLimitToggleGroup()).toBeNull();
  });

  it('expands safety limits when button is clicked', async () => {
    const {harness} = await createComponent();

    const collapsibleContainer = await harness.collapsibleContainer();
    await collapsibleContainer.expand();

    expect(await collapsibleContainer.isContentVisible()).toBeTrue();
    expect(await harness.crashLimitFormField()).not.toBeNull();
    expect(await harness.avgResultsPerClientLimitFormField()).not.toBeNull();
    expect(await harness.avgCpuSecondsPerClientLimitFormField()).not.toBeNull();
    expect(
      await harness.avgNetworkBytesPerClientLimitFormField(),
    ).not.toBeNull();
    expect(await harness.cpuTimeLimitToggleGroup()).not.toBeNull();
    expect(await harness.networkBytesLimitToggleGroup()).not.toBeNull();
  });

  describe('client limit', () => {
    it('does not render custom input when default values are selected', async () => {
      const {harness} = await createComponent();

      const toggleGroup = await harness.clientLimitToggleGroup();
      const smallSampleToggle = (
        await toggleGroup.getToggles({
          text: 'Small client sample',
        })
      )[0];
      await smallSampleToggle.check();

      expect(await harness.hasClientLimitInput()).toBeFalse();
    });

    it('does not render custom input when "unlimited" values are selected', async () => {
      const {harness} = await createComponent();

      const toggleGroup = await harness.clientLimitToggleGroup();
      const unlimitedToggle = (
        await toggleGroup.getToggles({text: 'All matching clients'})
      )[0];
      await unlimitedToggle.check();

      expect(await harness.hasClientLimitInput()).toBeFalse();
    });

    it('renders custom input when select custom', async () => {
      const {harness} = await createComponent();

      const toggleGroup = await harness.clientLimitToggleGroup();
      const customToggle = (await toggleGroup.getToggles({text: 'Custom'}))[0];
      await customToggle.check();

      expect(await harness.hasClientLimitInput()).toBeTrue();
    });
  });

  describe('rollout speed', () => {
    it('does not render custom input when default values are selected', async () => {
      const {harness} = await createComponent();

      const toggleGroup = await harness.rolloutSpeedToggleGroup();
      const standardToggle = (
        await toggleGroup.getToggles({
          text: 'Standard',
        })
      )[0];
      await standardToggle.check();

      expect(await harness.hasRolloutSpeedInput()).toBeFalse();
    });

    it('does not render custom input when "unlimited" value is selected', async () => {
      const {harness} = await createComponent();

      const toggleGroup = await harness.rolloutSpeedToggleGroup();
      const unlimitedToggle = (
        await toggleGroup.getToggles({text: 'Unlimited'})
      )[0];
      await unlimitedToggle.check();

      expect(await harness.hasRolloutSpeedInput()).toBeFalse();
    });

    it('renders custom input when select custom', async () => {
      const {harness} = await createComponent();

      const toggleGroup = await harness.rolloutSpeedToggleGroup();
      const customToggle = (await toggleGroup.getToggles({text: 'Custom'}))[0];
      await customToggle.check();

      expect(await harness.hasRolloutSpeedInput()).toBeTrue();
    });
  });

  describe('per client cpu limit', () => {
    it('does not render custom input when unlimited value is set', async () => {
      const {harness} = await createComponent(
        newSafetyLimits({
          perClientCpuLimit: BigInt(0),
        }),
      );

      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      expect(await harness.hasPerClientCpuLimitInput()).toBeFalse();
      const toggleGroup = await harness.cpuTimeLimitToggleGroup();
      const unlimitedToggle = (
        await toggleGroup!.getToggles({text: 'Unlimited'})
      )[0];
      expect(await unlimitedToggle.isChecked()).toBeTrue();
    });

    it('renders custom input when custom value is set', async () => {
      const {harness} = await createComponent(
        newSafetyLimits({
          perClientCpuLimit: BigInt(10),
        }),
      );

      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      expect(await harness.hasPerClientCpuLimitInput()).toBeTrue();
      const perClientCpuLimitInput = await harness.getPerClientCpuLimitInput();
      expect(await perClientCpuLimitInput.getValue()).toBe('10 s');
      const toggleGroup = await harness.cpuTimeLimitToggleGroup();
      const customToggle = (await toggleGroup!.getToggles({text: 'Custom'}))[0];
      expect(await customToggle.isChecked()).toBeTrue();
    });
  });

  describe('per client network bytes limit', () => {
    it('does not render custom input when unlimited value is set', async () => {
      const {harness} = await createComponent(
        newSafetyLimits({
          perClientNetworkBytesLimit: BigInt(0),
        }),
      );

      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      expect(await harness.hasPerClientNetworkBytesLimitInput()).toBeFalse();
      const toggleGroup = await harness.networkBytesLimitToggleGroup();
      const unlimitedToggle = (
        await toggleGroup!.getToggles({
          text: 'Unlimited',
        })
      )[0];
      expect(await unlimitedToggle.isChecked()).toBeTrue();
    });

    it('renders custom input when custom value is set', async () => {
      const {harness} = await createComponent(
        newSafetyLimits({
          perClientNetworkBytesLimit: BigInt(10), // not 0 = UNLIMITED
        }),
      );

      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      expect(await harness.hasPerClientNetworkBytesLimitInput()).toBeTrue();
      const perClientNetworkBytesLimitInput =
        await harness.getPerClientNetworkBytesLimitInput();
      expect(await perClientNetworkBytesLimitInput.getValue()).toBe('10 B');
      const toggleGroup = await harness.networkBytesLimitToggleGroup();
      const customToggle = (await toggleGroup!.getToggles({text: 'Custom'}))[0];
      expect(await customToggle.isChecked()).toBeTrue();
    });
  });

  it('can build the form state', async () => {
    const {harness, fixture} = await createComponent();

    const safetyLimits = await harness.collapsibleContainer();
    await safetyLimits.expand();

    const rolloutSpeedToggleGroup = await harness.rolloutSpeedToggleGroup();
    const unlimitedRolloutSpeedToggle = (
      await rolloutSpeedToggleGroup.getToggles({text: 'Unlimited'})
    )[0];
    await unlimitedRolloutSpeedToggle.check();

    const runOnButtonToggleGroup = await harness.clientLimitToggleGroup();
    const customClientLimitToggle = (
      await runOnButtonToggleGroup.getToggles({text: 'Custom'})
    )[0];
    await customClientLimitToggle.check();
    const customClientLimitInput = await harness.getClientLimitInput();
    await customClientLimitInput.setValue('2023');

    const expirationTimeInput = await harness.getExpiryTimeInput();
    await expirationTimeInput.setValue('14 d');

    const crashLimitInput = await harness.getCrashLimitInput();
    await crashLimitInput.setValue('100');

    const avgResultsPerClientLimitInput =
      await harness.getAvgResultsPerClientLimitInput();
    await avgResultsPerClientLimitInput.setValue('34');

    const avgCpuSecondsPerClientLimitInput =
      await harness.getAvgCpuSecondsPerClientLimitInput();
    await avgCpuSecondsPerClientLimitInput.setValue('56 s');

    const avgNetworkBytesPerClientLimitInput =
      await harness.getAvgNetworkBytesPerClientLimitInput();
    await avgNetworkBytesPerClientLimitInput.setValue('78 B');

    const cpuTimeLimitToggleGroup = await harness.cpuTimeLimitToggleGroup();
    const customCpuTimeLimitToggle = (
      await cpuTimeLimitToggleGroup!.getToggles({text: 'Custom'})
    )[0];
    await customCpuTimeLimitToggle.check();
    const perClientCpuLimitInput = await harness.getPerClientCpuLimitInput();
    await perClientCpuLimitInput.setValue('90 s');

    const networkBytesLimitToggleGroup =
      await harness.networkBytesLimitToggleGroup();
    const customNetworkBytesLimitToggle = (
      await networkBytesLimitToggleGroup!.getToggles({text: 'Custom'})
    )[0];
    await customNetworkBytesLimitToggle.check();
    const perClientNetworkBytesLimitInput =
      await harness.getPerClientNetworkBytesLimitInput();
    await perClientNetworkBytesLimitInput.setValue('13 B');

    expect(fixture.componentInstance.getFormState()).toEqual({
      clientRate: 0,
      clientLimit: BigInt(2023),
      expiryTime: BigInt(1209600),
      crashLimit: BigInt(100),
      avgResultsPerClientLimit: BigInt(34),
      avgCpuSecondsPerClientLimit: BigInt(56),
      avgNetworkBytesPerClientLimit: BigInt(78),
      perClientCpuLimit: BigInt(90),
      perClientNetworkBytesLimit: BigInt(13),
    });
  });

  describe('form validation', () => {
    it('shows error for missing expiration time', async () => {
      const {harness} = await createComponent();

      const expirationTimeInput = await harness.getExpiryTimeInput();
      await expirationTimeInput.setValue('');
      await expirationTimeInput.blur();

      const formField = await harness.expiryTimeFormField();
      expect(await formField?.getTextErrors()).toEqual(['Input is required.']);
    });

    it('shows error for <=0 expiration time', async () => {
      const {harness} = await createComponent();

      const expirationTimeInput = await harness.getExpiryTimeInput();
      await expirationTimeInput.setValue('0');
      await expirationTimeInput.blur();

      const formField = await harness.expiryTimeFormField();
      expect(await formField?.getTextErrors()).toEqual(['Minimum value is 1.']);
    });

    it('shows error for missing average CPU time per client', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const avgCpuSecondsPerClientLimitInput =
        await harness.getAvgCpuSecondsPerClientLimitInput();
      await avgCpuSecondsPerClientLimitInput.setValue('');

      const formField = await harness.avgCpuSecondsPerClientLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Input is required.']);
    });

    it('shows error for <=0 average CPU time per client', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const avgCpuSecondsPerClientLimitInput =
        await harness.getAvgCpuSecondsPerClientLimitInput();
      await avgCpuSecondsPerClientLimitInput.setValue('0');

      const formField = await harness.avgCpuSecondsPerClientLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Minimum value is 1.']);
    });

    it('shows error for missing average network usage per client', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const avgNetworkBytesPerClientLimitInput =
        await harness.getAvgNetworkBytesPerClientLimitInput();
      await avgNetworkBytesPerClientLimitInput.setValue('');

      const formField = await harness.avgNetworkBytesPerClientLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Input is required.']);
    });

    it('shows error for <=0 average network usage per client', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const avgNetworkBytesPerClientLimitInput =
        await harness.getAvgNetworkBytesPerClientLimitInput();
      await avgNetworkBytesPerClientLimitInput.setValue('0');

      const formField = await harness.avgNetworkBytesPerClientLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Minimum value is 1.']);
    });

    it('shows error for missing per client CPU time', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const cpuTimeLimitToggleGroup = await harness.cpuTimeLimitToggleGroup();
      const customCpuTimeLimitToggle = (
        await cpuTimeLimitToggleGroup!.getToggles({text: 'Custom'})
      )[0];
      await customCpuTimeLimitToggle.check();
      const perClientCpuLimitInput = await harness.getPerClientCpuLimitInput();
      await perClientCpuLimitInput.setValue('');

      const formField = await harness.perClientCpuLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Input is required.']);
    });

    it('shows error for <=0 per client CPU time', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const cpuTimeLimitToggleGroup = await harness.cpuTimeLimitToggleGroup();
      const customCpuTimeLimitToggle = (
        await cpuTimeLimitToggleGroup!.getToggles({text: 'Custom'})
      )[0];
      await customCpuTimeLimitToggle.check();
      const perClientCpuLimitInput = await harness.getPerClientCpuLimitInput();
      await perClientCpuLimitInput.setValue('0');

      const formField = await harness.perClientCpuLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Minimum value is 1.']);
    });

    it('shows error for missing average network usage per client', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const networkBytesLimitToggleGroup =
        await harness.networkBytesLimitToggleGroup();
      const customNetworkBytesLimitToggle = (
        await networkBytesLimitToggleGroup!.getToggles({text: 'Custom'})
      )[0];
      await customNetworkBytesLimitToggle.check();
      const perClientNetworkBytesLimitInput =
        await harness.getPerClientNetworkBytesLimitInput();
      await perClientNetworkBytesLimitInput.setValue('');

      const formField = await harness.perClientNetworkBytesLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Input is required.']);
    });

    it('shows error for <=0 network limit per client', async () => {
      const {harness} = await createComponent();
      const safetyLimits = await harness.collapsibleContainer();
      await safetyLimits.expand();

      const networkBytesLimitToggleGroup =
        await harness.networkBytesLimitToggleGroup();
      const customNetworkBytesLimitToggle = (
        await networkBytesLimitToggleGroup!.getToggles({text: 'Custom'})
      )[0];
      await customNetworkBytesLimitToggle.check();
      const perClientNetworkBytesLimitInput =
        await harness.getPerClientNetworkBytesLimitInput();
      await perClientNetworkBytesLimitInput.setValue('0');

      const formField = await harness.perClientNetworkBytesLimitFormField();
      expect(await formField?.getTextErrors()).toEqual(['Minimum value is 1.']);
    });
  });
});
