/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import 'jasmine';
import {Subject} from 'rxjs';
import {FlowDescriptor} from '../lib/models/flow';
import {FlowDescriptorMap} from './flow/flow_reducers';
import {FlowFacade} from './flow_facade';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface FlowFacadeMock extends I<FlowFacade> {
  flowDescriptorsSubject: Subject<FlowDescriptorMap>;
  selectedFlowSubject: Subject<FlowDescriptor|undefined>;
}

export function mockFlowFacade(): FlowFacadeMock {
  const flowDescriptorsSubject = new Subject<FlowDescriptorMap>();
  const selectedFlowSubject = new Subject<FlowDescriptor|undefined>();

  return {
    listFlowDescriptors: jasmine.createSpy('listFlowDescriptors'),
    flowDescriptorsSubject,
    flowDescriptors$: flowDescriptorsSubject.asObservable(),
    selectFlow: jasmine.createSpy('selectFlow'),
    unselectFlow: jasmine.createSpy('unselectFlow'),
    selectedFlowSubject,
    selectedFlow$: selectedFlowSubject.asObservable(),
  };
}
