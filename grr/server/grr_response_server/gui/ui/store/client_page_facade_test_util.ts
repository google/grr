/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {FlowDescriptor} from '@app/lib/models/flow';
import {ReplaySubject, Subject} from 'rxjs';

import {Client, ClientApproval} from '../lib/models/client';

import {ClientPageFacade, StartFlowState} from './client_page_facade';

export declare interface ClientPageFacadeMock extends
    Partial<ClientPageFacade> {
  selectedFlowDescriptorSubject: Subject<FlowDescriptor|undefined>;
  selectedClientSubject: Subject<Client>;
  startFlowStateSubject: Subject<StartFlowState>;
  latestApprovalSubject: Subject<ClientApproval>;
}

export function mockClientPageFacade(): ClientPageFacadeMock {
  const selectedFlowDescriptorSubject =
      new ReplaySubject<FlowDescriptor|undefined>();
  const selectedClientSubject = new ReplaySubject<Client>(1);
  const startFlowStateSubject = new ReplaySubject<StartFlowState>(1);
  const latestApprovalSubject = new ReplaySubject<ClientApproval>(1);
  startFlowStateSubject.next({state: 'request_not_sent'});

  return {
    startFlowConfiguration: jasmine.createSpy('startFlowConfiguration'),
    stopFlowConfiguration: jasmine.createSpy('stopFlowConfiguration'),
    selectedFlowDescriptorSubject,
    selectedFlowDescriptor$: selectedFlowDescriptorSubject.asObservable(),
    startFlow: jasmine.createSpy('startFlow'),
    scheduleFlow: jasmine.createSpy('scheduleFlow'),
    selectedClientSubject,
    selectedClient$: selectedClientSubject.asObservable(),
    startFlowStateSubject,
    startFlowState$: startFlowStateSubject.asObservable(),
    latestApprovalSubject,
    latestApproval$: latestApprovalSubject.asObservable(),
  };
}
