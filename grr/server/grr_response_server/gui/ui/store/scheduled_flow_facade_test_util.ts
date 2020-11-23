/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';
import {ScheduledFlow} from '../lib/models/flow';
import {ScheduledFlowFacade} from './scheduled_flow_facade';

export interface ScheduledFlowFacadeMock extends Partial<ScheduledFlowFacade> {
  readonly scheduledFlowsSubject: Subject<ReadonlyArray<ScheduledFlow>>;
}

export function mockScheduledFlowFacade(): ScheduledFlowFacadeMock {
  const scheduledFlowsSubject =
      new ReplaySubject<ReadonlyArray<ScheduledFlow>>();
  return {
    scheduledFlows$: scheduledFlowsSubject.asObservable(),
    scheduledFlowsSubject,
    selectSource: jasmine.createSpy('selectSource'),
    unscheduleFlow: jasmine.createSpy('unscheduleFlow'),
  };
}
