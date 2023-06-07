import {AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef, Component, OnDestroy, ViewChild} from '@angular/core';
import {Router} from '@angular/router';
import {filter, take, tap} from 'rxjs/operators';

import {RolloutForm} from '../../../components/hunt/rollout_form/rollout_form';
import {HuntState} from '../../../lib/models/hunt';
import {isNonNull} from '../../../lib/preconditions';
import {observeOnDestroy} from '../../../lib/reactive';
import {HuntPageGlobalStore} from '../../../store/hunt_page_global_store';

/**
 * Component displaying the details for a single hunt result.
 */
@Component({
  selector: 'modify-hunt',
  templateUrl: './modify_hunt.ng.html',
  styleUrls: ['./modify_hunt.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ModifyHunt implements OnDestroy, AfterViewInit {
  readonly ngOnDestroy = observeOnDestroy(this);
  protected readonly HuntState = HuntState;

  @ViewChild('rolloutForm', {static: false}) rolloutForm!: RolloutForm;

  constructor(
      private readonly huntPageGlobalStore: HuntPageGlobalStore,
      private readonly changeDetection: ChangeDetectorRef,
      private readonly router: Router,
  ) {}

  protected readonly hunt$ = this.huntPageGlobalStore.selectedHunt$;

  ngAfterViewInit() {
    this.huntPageGlobalStore.selectedHunt$
        .pipe(
            filter(isNonNull),
            // We don't want to reset the form on each poll, only once.
            take(1),
            tap(hunt => {
              this.rolloutForm.setFormState(hunt.safetyLimits);
            }),
            )
        .subscribe();
    this.changeDetection.detectChanges();
  }

  modifyAndContinue() {
    this.huntPageGlobalStore.modifyAndStartHunt(
        this.rolloutForm.getPartialLimits());
    // Close drawer
    this.router.navigate([{outlets: {'drawer': null}}], {replaceUrl: true});
  }
}