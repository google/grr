/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ApprovalConfig, ClientLabel} from '../lib/models/client';
import {FlowDescriptorMap} from '../lib/models/flow';

import {ConfigFacade} from './config_facade';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface ConfigFacadeMock extends I<ConfigFacade> {
  flowDescriptorsSubject: Subject<FlowDescriptorMap>;
  approvalConfigSubject: Subject<ApprovalConfig>;
  clientsLabelsSubject: Subject<ClientLabel[]>;
}

export function mockConfigFacade(): ConfigFacadeMock {
  const flowDescriptorsSubject = new ReplaySubject<FlowDescriptorMap>();
  const approvalConfigSubject = new ReplaySubject<ApprovalConfig>();
  const clientsLabelsSubject = new ReplaySubject<ClientLabel[]>();

  return {
    flowDescriptorsSubject,
    flowDescriptors$: flowDescriptorsSubject.asObservable(),
    approvalConfigSubject,
    approvalConfig$: approvalConfigSubject.asObservable(),
    clientsLabelsSubject,
    clientsLabels$: clientsLabelsSubject.asObservable(),
  };
}
