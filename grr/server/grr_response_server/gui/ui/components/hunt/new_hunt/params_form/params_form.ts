import {ChangeDetectionStrategy, Component, HostBinding, HostListener} from '@angular/core';
import {UntypedFormControl, UntypedFormGroup} from '@angular/forms';
import {Observable} from 'rxjs';

import {SafetyLimits} from '../../../../lib/models/hunt';
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
export class ParamsForm {
  @HostBinding('class.closed') hideContent = false;

  readonly defaultSafetyLimits$: Observable<SafetyLimits|undefined> =
      this.newHuntLocalStore.safetyLimits$;

  readonly controls = {
    clientRate: new UntypedFormControl(''),
    expiryTime: new UntypedFormControl(''),
    crashLimit: new UntypedFormControl(''),
    avgResultsPerClientLimit: new UntypedFormControl(''),
    avgCpuSecondsPerClientLimit: new UntypedFormControl(''),
    avgNetworkBytesPerClientLimit: new UntypedFormControl(''),
    cpuLimit: new UntypedFormControl(''),
    networkBytesLimit: new UntypedFormControl(''),
  };
  readonly form = new UntypedFormGroup(this.controls);

  clientLimit = 1000;
  customClientLimit = 0;
  customClientRate = -1;
  hideAdvancedParams = true;
  clientRateCustomInput = false;

  constructor(
      private readonly newHuntLocalStore: NewHuntLocalStore,
  ) {
    this.newHuntLocalStore.safetyLimits$.subscribe(safetyLimits => {
      this.form.setValue({
        clientRate: safetyLimits.clientRate,
        expiryTime: safetyLimits.expiryTime,
        crashLimit: safetyLimits.crashLimit,
        avgResultsPerClientLimit: safetyLimits.avgResultsPerClientLimit,
        avgCpuSecondsPerClientLimit: safetyLimits.avgCpuSecondsPerClientLimit,
        avgNetworkBytesPerClientLimit:
            safetyLimits.avgNetworkBytesPerClientLimit,
        cpuLimit: safetyLimits.cpuLimit,
        networkBytesLimit: safetyLimits.networkBytesLimit,
      });
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

  showClientRateCustomInput() {
    this.clientRateCustomInput = true;
  }

  hideClientRateCustomInput() {
    this.clientRateCustomInput = false;
  }

  buildSafetyLimits(): SafetyLimits {
    const clientRate = this.form.get('clientRate')!.value < 0 ?
        this.customClientRate :
        this.form.get('clientRate')!.value;
    const clientLimit =
        this.clientLimit < 0 ? this.customClientLimit : this.clientLimit;
    return {
      clientRate,
      clientLimit: BigInt(clientLimit),
      expiryTime: this.form.get('expiryTime')!.value,
      crashLimit: this.form.get('crashLimit')!.value,
      avgResultsPerClientLimit:
          this.form.get('avgResultsPerClientLimit')!.value,
      avgCpuSecondsPerClientLimit:
          this.form.get('avgCpuSecondsPerClientLimit')!.value,
      avgNetworkBytesPerClientLimit:
          this.form.get('avgNetworkBytesPerClientLimit')!.value,
      cpuLimit: this.form.get('cpuLimit')!.value,
      networkBytesLimit: this.form.get('networkBytesLimit')!.value,
    };
  }
}
