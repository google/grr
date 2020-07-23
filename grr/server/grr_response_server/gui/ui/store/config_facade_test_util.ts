/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ApprovalConfig} from '../lib/models/client';
import {FlowDescriptorMap} from '../lib/models/flow';

import {ConfigFacade} from './config_facade';
import {RdfValueDescriptor} from '@app/lib/api/api_interfaces';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface ConfigFacadeMock extends I<ConfigFacade> {
  flowDescriptorsSubject: Subject<FlowDescriptorMap>;
  approvalConfigSubject: Subject<ApprovalConfig>;
  rdfDescriptorsSubject: Subject<ReadonlyArray<RdfValueDescriptor>>;
}

export function mockConfigFacade(): ConfigFacadeMock {
  const flowDescriptorsSubject = new ReplaySubject<FlowDescriptorMap>();
  const approvalConfigSubject = new ReplaySubject<ApprovalConfig>();
  const rdfDescriptorsSubject = new ReplaySubject<ReadonlyArray<RdfValueDescriptor>>();

  return {
    flowDescriptorsSubject,
    flowDescriptors$: flowDescriptorsSubject.asObservable(),
    approvalConfigSubject,
    approvalConfig$: approvalConfigSubject.asObservable(),
    rdfDescriptorsSubject,
    rdfDescriptors$: rdfDescriptorsSubject.asObservable(),
  };
}
