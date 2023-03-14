import {ChangeDetectorRef, Component} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';

import {SafetyLimits} from '../../../lib/models/hunt';

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

type ControlNames = 'rolloutSpeed'|'clientRate'|'runOn'|'clientLimit';

/**
 * Provides the forms for hunt rollout params configuration.
 */
@Component({
  selector: 'app-rollout-form',
  templateUrl: './rollout_form.ng.html',
  styleUrls: ['./rollout_form.scss']
})
export class RolloutForm {
  readonly RolloutSpeed = RolloutSpeed;
  readonly RunOn = RunOn;

  defaultRolloutSpeed = RolloutSpeed.STANDARD;
  customClientRate = -1;
  defaultRunOn = RunOn.SAMPLE;
  customClientLimit = 0;

  readonly controls: {[key in ControlNames]: FormControl} = {
    rolloutSpeed:
        new FormControl(this.defaultRolloutSpeed, {nonNullable: true}),
    clientRate: new FormControl(this.customClientRate, {nonNullable: true}),
    runOn: new FormControl(this.defaultRunOn, {nonNullable: true}),
    clientLimit: new FormControl(
        BigInt(this.customClientLimit), {nonNullable: true}),
  };
  readonly form = new FormGroup(this.controls);

  setFormState(safetyLimits: SafetyLimits) {
    this.form.setValue({
      rolloutSpeed: getSpeed(safetyLimits.clientRate),
      clientRate: safetyLimits.clientRate,
      runOn:
          getRunOn(safetyLimits.clientLimit ?? BigInt(this.customClientLimit)),
      clientLimit: safetyLimits.clientLimit ?? BigInt(this.customClientLimit),
    });
    this.changeDetection.markForCheck();
  }

  getPartialLimits() {
    const clientRate = getRate(
        this.controls.rolloutSpeed.value, this.controls.clientRate.value);
    const clientLimit = getLimit(
        this.controls.runOn.value, BigInt(this.controls.clientLimit.value));
    return {clientRate, clientLimit};
  }

  constructor(
      private readonly changeDetection: ChangeDetectorRef,
  ) {}
}
