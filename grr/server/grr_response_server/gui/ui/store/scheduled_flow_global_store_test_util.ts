/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ScheduledFlow} from '../lib/models/flow';

import {ScheduledFlowGlobalStore} from './scheduled_flow_global_store';

export interface ScheduledFlowGlobalStoreMock extends
    Partial<ScheduledFlowGlobalStore> {
  readonly scheduledFlowsSubject: Subject<ReadonlyArray<ScheduledFlow>>;
}

export function mockScheduledFlowGlobalStore(): ScheduledFlowGlobalStoreMock {
  const scheduledFlowsSubject =
      new ReplaySubject<ReadonlyArray<ScheduledFlow>>();
  return {
    scheduledFlows$: scheduledFlowsSubject.asObservable(),
    scheduledFlowsSubject,
    selectSource: jasmine.createSpy('selectSource'),
    unscheduleFlow: jasmine.createSpy('unscheduleFlow'),
  };
}
