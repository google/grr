import {AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, HostBinding, HostListener, OnDestroy, ViewChild} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {Observable} from 'rxjs';
import {filter, map} from 'rxjs/operators';

import {toDurationUnit} from '../../../../components/form/duration_input/duration_conversion';
import {RolloutForm} from '../../../../components/hunt/rollout_form/rollout_form';
import {SafetyLimits} from '../../../../lib/models/hunt';
import {observeOnDestroy} from '../../../../lib/reactive';
import {NewHuntLocalStore} from '../../../../store/new_hunt_local_store';


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

  readonly defaultSafetyLimits$: Observable<SafetyLimits|undefined> =
      this.newHuntLocalStore.safetyLimits$;

  readonly controls = {
    'expiryTime': new FormControl(BigInt(0), {nonNullable: true}),
    'crashLimit': new FormControl(BigInt(0), {nonNullable: true}),
    'avgResultsPerClientLimit': new FormControl(BigInt(0), {nonNullable: true}),
    'avgCpuSecondsPerClientLimit': new FormControl(
        BigInt(0), {nonNullable: true}),
    'avgNetworkBytesPerClientLimit': new FormControl(
        BigInt(0), {nonNullable: true}),
    'perClientCpuLimit': new FormControl(BigInt(0), {nonNullable: true}),
    'perClientNetworkBytesLimit': new FormControl(
        BigInt(0), {nonNullable: true}),
  };
  readonly form = new FormGroup(this.controls);

  readonly formExpiryTimeSeconds$ = this.form.valueChanges.pipe(
      // durationInput is guaranteed to return a number.
      // It uses `parseDurationString` from
      // ../form/duration_input/duration_conversion.
      map(values => Number(values.expiryTime)),
      filter(time => time !== undefined && time !== null),
  );
  readonly durationFormattedParts$ = this.formExpiryTimeSeconds$.pipe(
      map(formTimeNumber => toDurationUnit(formTimeNumber, 'long')));
  readonly durationFormattedNumber$ = this.durationFormattedParts$.pipe(
      map(([durationOnly]) => durationOnly.toLocaleString()));
  readonly durationFormattedUnit$ =
      this.durationFormattedParts$.pipe(map(([, unitOnly]) => unitOnly));

  readonly formPerClientCpuLimitSeconds$ = this.form.valueChanges.pipe(
      // durationInput is guaranteed to return a number.
      // It uses `parseDurationString` from
      // ../form/duration_input/duration_conversion.
      map(values => Number(values.perClientCpuLimit)),
      filter(cpuLimit => cpuLimit !== undefined && cpuLimit !== null),
  );
  readonly perClientCpuLimitFormattedParts$ =
      this.formPerClientCpuLimitSeconds$.pipe(
          map(formNumber => toDurationUnit(formNumber, 'long')));
  readonly perClientCpuLimitFormattedNumber$ =
      this.perClientCpuLimitFormattedParts$.pipe(
          map(([numberOnly]) => numberOnly.toLocaleString()));
  readonly perClientCpuLimitFormattedUnit$ =
      this.perClientCpuLimitFormattedParts$.pipe(
          map(([, unitOnly]) => unitOnly));

  constructor(
      private readonly changeDetection: ChangeDetectorRef,
      private readonly newHuntLocalStore: NewHuntLocalStore,
  ) {}

  ngAfterViewInit() {
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
    this.rolloutForm.setFormState(safetyLimits);
    this.form.setValue({
      'expiryTime': safetyLimits.expiryTime,
      'crashLimit': safetyLimits.crashLimit,
      'avgResultsPerClientLimit': safetyLimits.avgResultsPerClientLimit,
      'avgCpuSecondsPerClientLimit': safetyLimits.avgCpuSecondsPerClientLimit,
      'avgNetworkBytesPerClientLimit':
          safetyLimits.avgNetworkBytesPerClientLimit,
      'perClientCpuLimit': safetyLimits.perClientCpuLimit,
      'perClientNetworkBytesLimit': safetyLimits.perClientNetworkBytesLimit,
    });
    this.changeDetection.markForCheck();
  }

  buildSafetyLimits(): SafetyLimits {
    const partialLimits = this.rolloutForm.getPartialLimits();
    return {
      ...partialLimits,
      expiryTime: BigInt(this.form.get('expiryTime')!.value),
      crashLimit: BigInt(this.form.get('crashLimit')!.value),

      avgResultsPerClientLimit:
          BigInt(this.form.get('avgResultsPerClientLimit')!.value),
      avgCpuSecondsPerClientLimit:
          BigInt(this.form.get('avgCpuSecondsPerClientLimit')!.value),
      avgNetworkBytesPerClientLimit:
          BigInt(this.form.get('avgNetworkBytesPerClientLimit')!.value),

      perClientCpuLimit: BigInt(this.form.get('perClientCpuLimit')!.value),
      perClientNetworkBytesLimit:
          BigInt(this.form.get('perClientNetworkBytesLimit')!.value),
    };
  }
}
