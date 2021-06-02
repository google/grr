import {Component, Input, OnDestroy} from '@angular/core';
import {Flow} from '@app/lib/models/flow';
import {ReplaySubject, Subject} from 'rxjs';
import {map} from 'rxjs/operators';

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

  readonly unsubscribe$ = new Subject<void>();

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

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();

    this.flow$.complete();
  }
}
