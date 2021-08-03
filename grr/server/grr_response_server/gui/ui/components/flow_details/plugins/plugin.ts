import {Component, Input, OnDestroy} from '@angular/core';
import {Flow} from '@app/lib/models/flow';
import {ReplaySubject} from 'rxjs';
import {map} from 'rxjs/operators';

import {observeOnDestroy} from '../../../lib/reactive';
import {makeLegacyLink} from '../../../lib/routing';

/**
 * Base class for all flow details plugins.
 */
@Component({template: ''})
export abstract class Plugin implements OnDestroy {
  private flowValue?: Flow;

  /**
   * Subject emitting new Flow values on every "flow"
   * binding change.
   */
  readonly flow$ = new ReplaySubject<Flow>(1);

  readonly fallbackUrl$ = this.flow$.pipe(map(flow => {
    const {flowId, clientId} = flow;
    return makeLegacyLink(`#/clients/${clientId}/flows/${flowId}`);
  }));

  readonly ngOnDestroy = observeOnDestroy(() => {
    this.flow$.complete();
  });

  /**
   * Flow input binding containing flow data information to display.
   */
  @Input()
  set flow(value: Flow) {
    this.flowValue = value;
    this.flow$.next(value);
  }

  get flow(): Flow {
    return this.flowValue!;
  }
}
