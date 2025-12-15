

import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  effect,
  inject,
  input,
  signal,
} from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms';
import {MatButtonToggleModule} from '@angular/material/button-toggle';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';

import {SafetyLimits} from '../../../lib/models/hunt';
import {HumanReadableByteSizePipe} from '../../../pipes/human_readable/human_readable_byte_size_pipe';
import {HumanReadableDurationPipe} from '../../../pipes/human_readable/human_readable_duration_pipe';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleState,
  CollapsibleTitle,
} from '../collapsible_container';
import {ByteValueAccessor} from '../form/byte_input/byte_value_accessor';
import {DurationValueAccessor} from '../form/duration_input/duration_value_accessor';
import {FormErrors, minValue, requiredInput} from '../form/form_validation';
import {
  ROLLOUT_SPEED_STANDARD,
  ROLLOUT_SPEED_UNLIMITED,
  SAMPLE_SIZE_SMALL,
  SAMPLE_SIZE_UNLIMITED,
} from './fleet_collection_arguments';

const UNLIMITED_INPUT = 0;

/**
 * Provides the forms for fleet collection rollout params configuration.
 */
@Component({
  selector: 'rollout-form',
  templateUrl: './rollout_form.ng.html',
  imports: [
    ByteValueAccessor,
    CollapsibleContainer,
    CollapsibleContent,
    CollapsibleTitle,
    CommonModule,
    DurationValueAccessor,
    FormErrors,
    FormsModule,
    HumanReadableByteSizePipe,
    HumanReadableDurationPipe,
    MatButtonToggleModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    ReactiveFormsModule,
  ],
  styleUrls: ['./rollout_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RolloutForm {
  private readonly changeDetection = inject(ChangeDetectorRef);

  initialSafetyLimits = input.required<SafetyLimits>();
  advancedParams = input<boolean>(true);

  protected readonly ROLLOUT_SPEED_STANDARD = ROLLOUT_SPEED_STANDARD;
  protected readonly ROLLOUT_SPEED_UNLIMITED = ROLLOUT_SPEED_UNLIMITED;
  protected customRolloutSpeed = signal<boolean>(false);

  protected readonly SAMPLE_SIZE_SMALL = SAMPLE_SIZE_SMALL;
  protected readonly SAMPLE_SIZE_UNLIMITED = SAMPLE_SIZE_UNLIMITED;
  protected customSampleSize = signal<boolean>(false);

  protected readonly UNLIMITED_INPUT = UNLIMITED_INPUT;
  protected customCpuTimeLimitPerClient = signal<boolean>(false);
  protected customNetworkBytesLimitPerClient = signal<boolean>(false);

  protected readonly CollapsibleState = CollapsibleState;

  readonly controls = {
    clientRate: new FormControl(ROLLOUT_SPEED_STANDARD, {
      nonNullable: true,
    }),
    clientLimit: new FormControl(SAMPLE_SIZE_SMALL, {nonNullable: true}),

    // Safety limits.
    expiryTime: new FormControl(0, {
      nonNullable: true,
      validators: [requiredInput(), minValue(1)],
    }),
    crashLimit: new FormControl(BigInt(0), {nonNullable: true}),
    avgResultsPerClientLimit: new FormControl(BigInt(0), {nonNullable: true}),
    avgCpuSecondsPerClientLimit: new FormControl(0, {
      nonNullable: true,
      validators: [requiredInput(), minValue(1)],
    }),
    avgNetworkBytesPerClientLimit: new FormControl(0, {
      nonNullable: true,
      validators: [requiredInput(), minValue(1)],
    }),
    perClientCpuLimit: new FormControl(0, {
      nonNullable: true,
      validators: [requiredInput(), minValue(1)],
    }),
    perClientNetworkBytesLimit: new FormControl(0, {
      nonNullable: true,
      validators: [requiredInput(), minValue(1)],
    }),
  };
  readonly form = new FormGroup(this.controls);

  constructor() {
    effect(() => {
      this.setFormState(this.initialSafetyLimits());
    });
  }

  setFixedSampleSize(value: bigint) {
    this.controls.clientLimit.setValue(value);
    this.customSampleSize.set(false);
  }

  setFixedRolloutSpeed(value: number) {
    this.controls.clientRate.setValue(value);
    this.customRolloutSpeed.set(false);
  }

  setUnlimitedCpuTimeLimitPerClient() {
    this.controls.perClientCpuLimit.setValue(UNLIMITED_INPUT);
    this.customCpuTimeLimitPerClient.set(false);
  }

  setUnlimitedNetworkBytesLimitPerClient() {
    this.controls.perClientNetworkBytesLimit.setValue(UNLIMITED_INPUT);
    this.customNetworkBytesLimitPerClient.set(false);
  }

  setFormState(safetyLimits: SafetyLimits) {
    this.customRolloutSpeed.set(
      safetyLimits.clientRate !== ROLLOUT_SPEED_UNLIMITED &&
        safetyLimits.clientRate !== ROLLOUT_SPEED_STANDARD,
    );
    this.customSampleSize.set(
      safetyLimits.clientLimit !== SAMPLE_SIZE_UNLIMITED &&
        safetyLimits.clientLimit !== SAMPLE_SIZE_SMALL,
    );
    this.customCpuTimeLimitPerClient.set(
      Number(safetyLimits.perClientCpuLimit) !== UNLIMITED_INPUT,
    );
    this.customNetworkBytesLimitPerClient.set(
      Number(safetyLimits.perClientNetworkBytesLimit) !== UNLIMITED_INPUT,
    );

    this.form.setValue({
      clientRate: safetyLimits.clientRate,
      clientLimit: safetyLimits.clientLimit,

      expiryTime: Number(safetyLimits.expiryTime),
      crashLimit: safetyLimits.crashLimit,
      avgResultsPerClientLimit: safetyLimits.avgResultsPerClientLimit,
      avgCpuSecondsPerClientLimit: Number(
        safetyLimits.avgCpuSecondsPerClientLimit,
      ),
      avgNetworkBytesPerClientLimit: Number(
        safetyLimits.avgNetworkBytesPerClientLimit,
      ),
      perClientCpuLimit: Number(safetyLimits.perClientCpuLimit),
      perClientNetworkBytesLimit: Number(
        safetyLimits.perClientNetworkBytesLimit,
      ),
    });

    this.changeDetection.markForCheck();
  }

  getFormState(): SafetyLimits {
    return {
      clientRate: this.controls.clientRate.value,
      clientLimit: BigInt(this.controls.clientLimit.value),

      expiryTime: BigInt(this.controls.expiryTime.value),
      crashLimit: BigInt(this.controls.crashLimit.value),

      avgResultsPerClientLimit: BigInt(
        this.controls.avgResultsPerClientLimit.value,
      ),
      avgCpuSecondsPerClientLimit: BigInt(
        this.controls.avgCpuSecondsPerClientLimit.value,
      ),
      avgNetworkBytesPerClientLimit: BigInt(
        this.controls.avgNetworkBytesPerClientLimit.value,
      ),

      perClientCpuLimit: BigInt(this.controls.perClientCpuLimit.value),
      perClientNetworkBytesLimit: BigInt(
        this.controls.perClientNetworkBytesLimit.value,
      ),
    };
  }
}
