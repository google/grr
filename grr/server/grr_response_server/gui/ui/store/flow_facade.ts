import {Injectable} from '@angular/core';
import {Store} from '@ngrx/store';
import {Observable} from 'rxjs';
import {filter} from 'rxjs/operators';

import {FlowDescriptor} from '../lib/models/flow';

import * as actions from './flow/flow_actions';
import {FlowDescriptorMap, FlowState} from './flow/flow_reducers';
import * as selectors from './flow/flow_selectors';


/** Facade for flow-related API calls. */
@Injectable()
export class FlowFacade {
  constructor(private readonly store: Store<FlowState>) {}

  listFlowDescriptors() {
    this.store.dispatch(actions.listFlowDescriptors());
  }

  readonly flowDescriptors$: Observable<FlowDescriptorMap> =
      this.store.select(selectors.flowDescriptors)
          .pipe(
              filter((fds): fds is FlowDescriptorMap => fds !== undefined),
          );

  selectFlow(name: string, args?: unknown) {
    this.store.dispatch(actions.selectFlow({name, args}));
  }

  unselectFlow() {
    this.store.dispatch(actions.unselectFlow());
  }

  readonly selectedFlow$: Observable<FlowDescriptor|undefined> =
      this.store.select(selectors.selectedFlow);
}
