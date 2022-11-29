import {ChangeDetectionStrategy, ChangeDetectorRef, Component, HostBinding, HostListener} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Observable} from 'rxjs';

import {SafetyLimits} from '../../../../lib/models/hunt';
import {NewHuntLocalStore} from '../../../../store/new_hunt_local_store';

enum RolloutSpeed {
  UNLIMITED = 'Unlimited',
  STANDARD = 'Standard',
  CUSTOM = 'Custom',
}

function getSpeed(rate: number): RolloutSpeed {
  switch (rate) {
    case 0:
      return RolloutSpeed.UNLIMITED;
    case 200:
      return RolloutSpeed.STANDARD;
    default:
      return RolloutSpeed.CUSTOM;
  }
}

function getRate(speed: RolloutSpeed, rate: number): number {
  switch (speed) {
    case RolloutSpeed.UNLIMITED:
      return 0;
    case RolloutSpeed.STANDARD:
      return 200;
    default:
      return rate;
  }
}

enum RunOn {
  ALL_CLIENTS = 'All matching clients',
  SAMPLE = 'Small sample',
  CUSTOM = 'Custom',
}

const SAMPLE_SIZE = 1000;

function getRunOn(limit: bigint): RunOn {
  switch (limit) {
    case BigInt(0):
      return RunOn.ALL_CLIENTS;
    case BigInt(SAMPLE_SIZE):
      return RunOn.SAMPLE;
    default:
      return RunOn.CUSTOM;
  }
}

function getLimit(runOn: RunOn, limit: bigint): bigint {
  switch (runOn) {
    case RunOn.ALL_CLIENTS:
      return BigInt(0);
    case RunOn.SAMPLE:
      return BigInt(SAMPLE_SIZE);
    default:
      return limit;
  }
}

/**
 * Provides the forms for new hunt params configuration.
 */
@Component({
  selector: 'app-params-form',
  templateUrl: './params_form.ng.html',
  styleUrls: ['./params_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [NewHuntLocalStore],
})
export class ParamsForm {
  @HostBinding('class.closed') hideContent = false;

  readonly RolloutSpeed = RolloutSpeed;
  readonly RunOn = RunOn;

  defaultRolloutSpeed = RolloutSpeed.STANDARD;
  customClientRate = -1;
  defaultRunOn = RunOn.SAMPLE;
  customClientLimit = 0;
  hideAdvancedParams = true;

  readonly defaultSafetyLimits$: Observable<SafetyLimits|undefined> =
      this.newHuntLocalStore.safetyLimits$;

  readonly controls = {
    'rolloutSpeed':
        new FormControl(this.defaultRolloutSpeed, {nonNullable: true}),
    'clientRate': new FormControl(this.customClientRate, {nonNullable: true}),
    'runOn': new FormControl(this.defaultRunOn, {nonNullable: true}),
    'clientLimit': new FormControl(
        BigInt(this.customClientLimit), {nonNullable: true}),
    'expiryTime': new FormControl(BigInt(0), {nonNullable: true}),
    'crashLimit': new FormControl(BigInt(0), {nonNullable: true}),
    'avgResultsPerClientLimit': new FormControl(BigInt(0), {nonNullable: true}),
    'avgCpuSecondsPerClientLimit': new FormControl(
        BigInt(0), {nonNullable: true}),
    'avgNetworkBytesPerClientLimit': new FormControl(
        BigInt(0), {nonNullable: true}),
    'cpuLimit': new FormControl(BigInt(0), {nonNullable: true}),
    'networkBytesLimit': new FormControl(BigInt(0), {nonNullable: true}),
  };
  readonly form = new FormGroup(this.controls);

  constructor(
      private readonly changeDetection: ChangeDetectorRef,
      private readonly newHuntLocalStore: NewHuntLocalStore,
  ) {
    this.newHuntLocalStore.safetyLimits$.subscribe(safetyLimits => {
      this.setFormState(safetyLimits);
    });
  }

  @HostListener('click')
  onClick(event: Event) {
    this.showForm(event);
  }

  toggleForm(event: Event) {
    this.hideContent = !this.hideContent;
    event.stopPropagation();
  }

  showForm(event: Event) {
    if (this.hideContent) {
      this.hideContent = false;
      event.stopPropagation();
    }
  }

  toggleAdvancedParams() {
    this.hideAdvancedParams = !this.hideAdvancedParams;
  }

  setFormState(safetyLimits: SafetyLimits) {
    this.form.setValue({
      'rolloutSpeed': getSpeed(safetyLimits.clientRate),
      'clientRate': safetyLimits.clientRate,
      'runOn':
          getRunOn(safetyLimits.clientLimit ?? BigInt(this.customClientLimit)),
      'clientLimit': safetyLimits.clientLimit ?? BigInt(this.customClientLimit),
      'expiryTime': safetyLimits.expiryTime,
      'crashLimit': safetyLimits.crashLimit,
      'avgResultsPerClientLimit': safetyLimits.avgResultsPerClientLimit,
      'avgCpuSecondsPerClientLimit': safetyLimits.avgCpuSecondsPerClientLimit,
      'avgNetworkBytesPerClientLimit':
          safetyLimits.avgNetworkBytesPerClientLimit,
      'cpuLimit': safetyLimits.cpuLimit,
      'networkBytesLimit': safetyLimits.networkBytesLimit,
    });
    this.changeDetection.markForCheck();
  }

  buildSafetyLimits(): SafetyLimits {
    const clientRate = getRate(
        this.form.get('rolloutSpeed')!.value,
        this.form.get('clientRate')!.value);
    const clientLimit = getLimit(
        this.form.get('runOn')!.value,
        BigInt(this.form.get('clientLimit')!.value));

    return {
      clientRate,
      clientLimit,
      expiryTime: BigInt(this.form.get('expiryTime')!.value),
      crashLimit: BigInt(this.form.get('crashLimit')!.value),
      avgResultsPerClientLimit:
          BigInt(this.form.get('avgResultsPerClientLimit')!.value),
      avgCpuSecondsPerClientLimit:
          BigInt(this.form.get('avgCpuSecondsPerClientLimit')!.value),
      avgNetworkBytesPerClientLimit:
          BigInt(this.form.get('avgNetworkBytesPerClientLimit')!.value),
      cpuLimit: BigInt(this.form.get('cpuLimit')!.value),
      networkBytesLimit: BigInt(this.form.get('networkBytesLimit')!.value),
    };
  }
}
