import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  HostBinding,
  HostListener,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Observable} from 'rxjs';

import {ByteFormControl} from '../../../../components/form/byte_input/byte_form_control';
import {DurationFormControl} from '../../../../components/form/duration_input/duration_form_control';
import {RolloutForm} from '../../../../components/hunt/rollout_form/rollout_form';
import {SafetyLimits} from '../../../../lib/models/hunt';
import {observeOnDestroy} from '../../../../lib/reactive';
import {NewHuntLocalStore} from '../../../../store/new_hunt_local_store';

enum InputToggle {
  UNLIMITED = 'Unlimited',
  CUSTOM = 'Custom',
}

const UNLIMITED_INPUT = BigInt(0);

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
export class ParamsForm implements AfterViewInit, OnDestroy {
  readonly ngOnDestroy = observeOnDestroy(this);

  @HostBinding('class.closed') hideContent = false;
  @ViewChild('rolloutForm', {static: false}) rolloutForm!: RolloutForm;

  hideAdvancedParams = true;

  readonly defaultSafetyLimits$: Observable<SafetyLimits | undefined> =
    this.newHuntLocalStore.defaultSafetyLimits$;

  readonly controls = {
    expiryTime: new DurationFormControl(BigInt(0), {
      nonNullable: true,
      validators: [DurationFormControl.defaultTimeValidator()],
    }),
    crashLimit: new FormControl(BigInt(0), {nonNullable: true}),
    avgResultsPerClientLimit: new FormControl(BigInt(0), {nonNullable: true}),
    avgCpuSecondsPerClientLimit: new DurationFormControl(BigInt(0), {
      nonNullable: true,
      validators: [DurationFormControl.defaultTimeValidator()],
    }),
    avgNetworkBytesPerClientLimit: new DurationFormControl(BigInt(0), {
      nonNullable: true,
      validators: [ByteFormControl.byteValidator()],
    }),
    perClientCpuLimitToggle: new FormControl(InputToggle.UNLIMITED, {
      nonNullable: true,
    }),
    perClientCpuLimit: new DurationFormControl(BigInt(0), {
      nonNullable: true,
      validators: [DurationFormControl.defaultTimeValidator()],
    }),
    perClientNetworkBytesLimitToggle: new FormControl(InputToggle.UNLIMITED, {
      nonNullable: true,
    }),
    perClientNetworkBytesLimit: new ByteFormControl(BigInt(0), {
      nonNullable: true,
      validators: [ByteFormControl.byteValidator()],
    }),
  };
  readonly form = new FormGroup(this.controls);

  readonly InputToggle = InputToggle;

  constructor(
    private readonly changeDetection: ChangeDetectorRef,
    private readonly newHuntLocalStore: NewHuntLocalStore,
  ) {}

  ngAfterViewInit() {
    this.newHuntLocalStore.defaultSafetyLimits$.subscribe((safetyLimits) => {
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
    this.rolloutForm.setFormState(safetyLimits);
    this.form.setValue({
      expiryTime: safetyLimits.expiryTime,
      crashLimit: safetyLimits.crashLimit,
      avgResultsPerClientLimit: safetyLimits.avgResultsPerClientLimit,
      avgCpuSecondsPerClientLimit: safetyLimits.avgCpuSecondsPerClientLimit,
      avgNetworkBytesPerClientLimit: safetyLimits.avgNetworkBytesPerClientLimit,
      perClientCpuLimitToggle:
        safetyLimits.perClientCpuLimit === UNLIMITED_INPUT
          ? InputToggle.UNLIMITED
          : InputToggle.CUSTOM,
      perClientCpuLimit: safetyLimits.perClientCpuLimit,
      perClientNetworkBytesLimitToggle:
        safetyLimits.perClientNetworkBytesLimit === UNLIMITED_INPUT
          ? InputToggle.UNLIMITED
          : InputToggle.CUSTOM,
      perClientNetworkBytesLimit: safetyLimits.perClientNetworkBytesLimit,
    });
    this.changeDetection.markForCheck();
  }

  buildSafetyLimits(): SafetyLimits {
    const partialLimits = this.rolloutForm.getPartialLimits();
    return {
      ...partialLimits,
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

      perClientCpuLimit:
        this.controls.perClientCpuLimitToggle.value === InputToggle.UNLIMITED
          ? UNLIMITED_INPUT
          : BigInt(this.controls.perClientCpuLimit.value),
      perClientNetworkBytesLimit:
        this.controls.perClientNetworkBytesLimitToggle.value ===
        InputToggle.UNLIMITED
          ? UNLIMITED_INPUT
          : BigInt(this.controls.perClientNetworkBytesLimit.value),
    };
  }
}
