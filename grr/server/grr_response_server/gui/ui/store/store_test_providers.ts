import {Provider} from '@angular/core';
import {TestBed} from '@angular/core/testing';

import {ApprovalPageGlobalStore} from './approval_page_global_store';
import {mockApprovalPageGlobalStore} from './approval_page_global_store_test_util';
import {ClientDetailsGlobalStore} from './client_details_global_store';
import {mockClientDetailsGlobalStore} from './client_details_global_store_test_util';
import {ClientPageGlobalStore} from './client_page_global_store';
import {mockClientPageGlobalStore} from './client_page_global_store_test_util';
import {ClientSearchGlobalStore} from './client_search_global_store';
import {mockClientSearchGlobalStore} from './client_search_global_store_test_util';
import {ConfigGlobalStore} from './config_global_store';
import {mockConfigGlobalStore} from './config_global_store_test_util';
import {FileDetailsLocalStore} from './file_details_local_store';
import {mockFileDetailsLocalStore} from './file_details_local_store_test_util';
import {FlowResultsLocalStore} from './flow_results_local_store';
import {mockFlowResultsLocalStore} from './flow_results_local_store_test_util';
import {HomePageGlobalStore} from './home_page_global_store';
import {mockHomePageGlobalStore} from './home_page_global_store_test_util';
import {ScheduledFlowGlobalStore} from './scheduled_flow_global_store';
import {mockScheduledFlowGlobalStore} from './scheduled_flow_global_store_test_util';
import {SelectedClientGlobalStore} from './selected_client_global_store';
import {mockSelectedClientGlobalStore} from './selected_client_global_store_test_util';
import {MockStore} from './store_test_util';
import {UserGlobalStore} from './user_global_store';
import {mockUserGlobalStore} from './user_global_store_test_util';

/** MockStore providers for Stores. */
export const STORE_PROVIDERS: Provider[] = [
  {provide: ApprovalPageGlobalStore, useFactory: mockApprovalPageGlobalStore},
  {provide: ClientDetailsGlobalStore, useFactory: mockClientDetailsGlobalStore},
  {provide: ClientPageGlobalStore, useFactory: mockClientPageGlobalStore},
  {provide: ClientSearchGlobalStore, useFactory: mockClientSearchGlobalStore},
  {provide: ConfigGlobalStore, useFactory: mockConfigGlobalStore},
  {provide: FileDetailsLocalStore, useFactory: mockFileDetailsLocalStore},
  {provide: FlowResultsLocalStore, useFactory: mockFlowResultsLocalStore},
  {provide: HomePageGlobalStore, useFactory: mockHomePageGlobalStore},
  {provide: ScheduledFlowGlobalStore, useFactory: mockScheduledFlowGlobalStore},
  {
    provide: SelectedClientGlobalStore,
    useFactory: mockSelectedClientGlobalStore
  },
  {provide: UserGlobalStore, useFactory: mockUserGlobalStore},
];

interface Constructor<ClassType> {
  new(...args: never[]): ClassType;
}

/** Injects the MockStore for the given Store class. */
export function injectMockStore<T>(cls: Constructor<T>): MockStore<T> {
  const mockStore = TestBed.inject(cls) as MockStore<T>;

  if (!mockStore.mockedObservables) {
    const val = JSON.stringify(mockStore).slice(0, 100);
    const type = mockStore?.constructor?.name ?? typeof mockStore;

    throw new Error(`TestBed.inject(${cls.name}) returned ${val} of type ${
        type}, which does not look like MockStore<${
        cls.name}>. Did you register MockStore providers?`);
  }

  return mockStore;
}
