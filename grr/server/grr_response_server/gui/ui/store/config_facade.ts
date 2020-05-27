import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {Observable} from 'rxjs';
import {filter, shareReplay, tap} from 'rxjs/operators';

import {ApprovalConfig} from '../lib/models/client';
import {FlowDescriptorMap} from '../lib/models/flow';

import * as actions from './config/config_actions';
import {ConfigState} from './config/config_reducers';
import * as selectors from './config/config_selectors';


/** Facade to retrieve general purpose configuration and backend data. */
@Injectable({
  providedIn: 'root',
})
export class ConfigFacade {
  constructor(private readonly store: Store<ConfigState>) {}

  readonly flowDescriptors$: Observable<FlowDescriptorMap> =
      this.store.select(selectors.flowDescriptors)
          .pipe(
              tap((fds) => {
                // When FlowDescriptors have not been loaded yet, trigger the
                // loading as a side-effect of this subscription.
                if (fds === undefined) {
                  this.store.dispatch(actions.listFlowDescriptors());
                }
              }),
              filter((fds): fds is FlowDescriptorMap => fds !== undefined),
              shareReplay(1),
          );

  readonly approvalConfig$: Observable<ApprovalConfig> =
      this.store.select(selectors.approvalConfig)
          .pipe(
              tap((approvalConfig) => {
                if (approvalConfig === undefined) {
                  this.store.dispatch(actions.fetchApprovalConfig());
                }
              }),
              filter((ac): ac is ApprovalConfig => ac !== undefined),
              shareReplay(1),
          );
}
