/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {FlowDescriptor, FlowListEntry, ScheduledFlow} from '@app/lib/models/flow';
import {ReplaySubject, Subject} from 'rxjs';

import {Client, ClientApproval} from '../lib/models/client';

import {ClientPageFacade, StartFlowState} from './client_page_facade';

export declare interface ClientPageFacadeMock extends
    Partial<ClientPageFacade> {
  readonly selectedFlowDescriptorSubject: Subject<FlowDescriptor|undefined>;
  readonly selectedClientSubject: Subject<Client>;
  readonly startFlowStateSubject: Subject<StartFlowState>;
  readonly latestApprovalSubject: Subject<ClientApproval|undefined>;
  readonly scheduledFlowsSubject: Subject<ReadonlyArray<ScheduledFlow>>;
  readonly approverSuggestionsSubject: Subject<ReadonlyArray<string>>;
  readonly lastRemovedClientLabelSubject: Subject<string>;
  readonly flowListEntriesSubject: Subject<ReadonlyArray<FlowListEntry>>;
}

export function mockClientPageFacade(): ClientPageFacadeMock {
  const selectedFlowDescriptorSubject =
      new ReplaySubject<FlowDescriptor|undefined>();
  const selectedClientSubject = new ReplaySubject<Client>(1);
  const startFlowStateSubject = new ReplaySubject<StartFlowState>(1);
  const latestApprovalSubject = new ReplaySubject<ClientApproval|undefined>(1);
  const scheduledFlowsSubject =
      new ReplaySubject<ReadonlyArray<ScheduledFlow>>(1);
  const approverSuggestionsSubject =
      new ReplaySubject<ReadonlyArray<string>>(1);
  const lastRemovedClientLabelSubject = new ReplaySubject<string>(1);
  const flowListEntriesSubject = new Subject<ReadonlyArray<FlowListEntry>>();

  latestApprovalSubject.next(undefined);
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
    scheduledFlowsSubject,
    scheduledFlows$: scheduledFlowsSubject.asObservable(),
    unscheduleFlow: jasmine.createSpy('unscheduleFlow'),
    suggestApprovers: jasmine.createSpy('suggestApprovers'),
    approverSuggestionsSubject,
    approverSuggestions$: approverSuggestionsSubject.asObservable(),
    requestApproval: jasmine.createSpy('requestApproval'),
    removeClientLabel: jasmine.createSpy('removeClientLabel'),
    addClientLabel: jasmine.createSpy('addClientLabel'),
    lastRemovedClientLabelSubject,
    lastRemovedClientLabel$: lastRemovedClientLabelSubject.asObservable(),
    selectClient: jasmine.createSpy('selectClient'),
    flowListEntriesSubject,
    flowListEntries$: flowListEntriesSubject.asObservable(),
  };
}
