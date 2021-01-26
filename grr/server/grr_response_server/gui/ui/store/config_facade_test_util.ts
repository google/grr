/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {ReplaySubject, Subject} from 'rxjs';

import {ApiUiConfig} from '../lib/api/api_interfaces';
import {ApprovalConfig} from '../lib/models/client';
import {ArtifactDescriptorMap, FlowDescriptorMap} from '../lib/models/flow';

import {ConfigFacade} from './config_facade';

type I<T> = {
  [key in keyof T]: T[key];
};

export declare interface ConfigFacadeMock extends I<ConfigFacade> {
  flowDescriptorsSubject: Subject<FlowDescriptorMap>;
  artifactDescriptorsSubject: Subject<ArtifactDescriptorMap>;
  approvalConfigSubject: Subject<ApprovalConfig>;
  uiConfigSubject: Subject<ApiUiConfig>;
  clientsLabelsSubject: Subject<string[]>;
}

export function mockConfigFacade(): ConfigFacadeMock {
  const flowDescriptorsSubject = new ReplaySubject<FlowDescriptorMap>();
  const artifactDescriptorsSubject = new ReplaySubject<ArtifactDescriptorMap>();
  const approvalConfigSubject = new ReplaySubject<ApprovalConfig>();
  const uiConfigSubject = new ReplaySubject<ApiUiConfig>();
  const clientsLabelsSubject = new ReplaySubject<string[]>();

  return {
    flowDescriptorsSubject,
    flowDescriptors$: flowDescriptorsSubject.asObservable(),
    artifactDescriptorsSubject,
    artifactDescriptors$: artifactDescriptorsSubject.asObservable(),
    approvalConfigSubject,
    approvalConfig$: approvalConfigSubject.asObservable(),
    uiConfigSubject,
    uiConfig$: uiConfigSubject.asObservable(),
    clientsLabelsSubject,
    clientsLabels$: clientsLabelsSubject.asObservable(),
  };
}
