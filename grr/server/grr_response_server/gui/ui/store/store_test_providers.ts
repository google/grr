import {DebugElement, Provider} from '@angular/core';
import {TestBed} from '@angular/core/testing';

import {ApprovalPageGlobalStore} from './approval_page_global_store';
import {mockApprovalPageGlobalStore} from './approval_page_global_store_test_util';
import {ClientDetailsGlobalStore} from './client_details_global_store';
import {mockClientDetailsGlobalStore} from './client_details_global_store_test_util';
import {ClientPageGlobalStore} from './client_page_global_store';
import {mockClientPageGlobalStore} from './client_page_global_store_test_util';
import {ClientSearchLocalStore} from './client_search_local_store';
import {mockClientSearchLocalStore} from './client_search_local_store_test_util';
import {ConfigGlobalStore} from './config_global_store';
import {mockConfigGlobalStore} from './config_global_store_test_util';
import {FileDetailsLocalStore} from './file_details_local_store';
import {mockFileDetailsLocalStore} from './file_details_local_store_test_util';
import {FlowResultsLocalStore} from './flow_results_local_store';
import {mockFlowResultsLocalStore} from './flow_results_local_store_test_util';
import {HomePageGlobalStore} from './home_page_global_store';
import {mockHomePageGlobalStore} from './home_page_global_store_test_util';
import {HuntApprovalPageGlobalStore} from './hunt_approval_page_global_store';
import {mockHuntApprovalPageGlobalStore} from './hunt_approval_page_global_store_test_util';
import {HuntOverviewPageLocalStore} from './hunt_overview_page_local_store';
import {NewHuntLocalStore} from './new_hunt_local_store';
import {mockNewHuntLocalStore} from './new_hunt_local_store_test_util';
import {RecentClientFlowsLocalStore} from './recent_client_flows_local_store';
import {mockRecentClientFlowsLocalStore} from './recent_client_flows_local_store_test_util';
import {ScheduledFlowGlobalStore} from './scheduled_flow_global_store';
import {mockScheduledFlowGlobalStore} from './scheduled_flow_global_store_test_util';
import {SelectedClientGlobalStore} from './selected_client_global_store';
import {mockSelectedClientGlobalStore} from './selected_client_global_store_test_util';
import {mockStore, MockStore} from './store_test_util';
import {UserGlobalStore} from './user_global_store';
import {mockUserGlobalStore} from './user_global_store_test_util';
import {VfsViewLocalStore} from './vfs_view_local_store';
import {mockVfsViewLocalStore} from './vfs_view_local_store_test_util';

/** MockStore providers for Stores. */
export const STORE_PROVIDERS: Provider[] = [
  {provide: ApprovalPageGlobalStore, useFactory: mockApprovalPageGlobalStore},
  {
    provide: HuntApprovalPageGlobalStore,
    useFactory: mockHuntApprovalPageGlobalStore
  },
  {provide: ClientDetailsGlobalStore, useFactory: mockClientDetailsGlobalStore},
  {provide: ClientPageGlobalStore, useFactory: mockClientPageGlobalStore},
  {provide: ClientSearchLocalStore, useFactory: mockClientSearchLocalStore},
  {
    provide: RecentClientFlowsLocalStore,
    useFactory: mockRecentClientFlowsLocalStore
  },
  {provide: ConfigGlobalStore, useFactory: mockConfigGlobalStore},
  {provide: FileDetailsLocalStore, useFactory: mockFileDetailsLocalStore},
  {provide: FlowResultsLocalStore, useFactory: mockFlowResultsLocalStore},
  {provide: HomePageGlobalStore, useFactory: mockHomePageGlobalStore},
  {provide: ScheduledFlowGlobalStore, useFactory: mockScheduledFlowGlobalStore},
  {provide: VfsViewLocalStore, useFactory: mockVfsViewLocalStore},
  {
    provide: SelectedClientGlobalStore,
    useFactory: mockSelectedClientGlobalStore
  },
  {provide: UserGlobalStore, useFactory: mockUserGlobalStore},
  {provide: NewHuntLocalStore, useFactory: mockNewHuntLocalStore},
  {
    provide: HuntOverviewPageLocalStore,
    useFactory: mockHuntOverviewPageLocalStore,
  },
];

interface Constructor<ClassType> {
  new(...args: never[]): ClassType;
}

/** Injects the MockStore for the given Store class. */
export function injectMockStore<T>(
    cls: Constructor<T>, scope?: TestBed|DebugElement): MockStore<T> {
  let mockStore: MockStore<T>;
  if (scope && (scope as DebugElement).injector) {
    mockStore = (scope as DebugElement).injector.get(cls) as MockStore<T>;
  } else {
    mockStore = ((scope as TestBed) ?? TestBed).inject(cls) as MockStore<T>;
  }

  if (!mockStore.mockedObservables) {
    let val: string;

    try {
      val = JSON.stringify(mockStore).slice(0, 100);
    } catch (e) {
      val = String(mockStore);
    }

    const type = mockStore?.constructor?.name ?? typeof mockStore;

    throw new Error(`TestBed.inject(${cls.name}) returned ${val} of type ${
        type}, which does not look like MockStore<${
        cls.name}>. Did you register MockStore providers?`);
  }

  return mockStore;
}

/** Mocks a HuntOverviewPageLocalStore. */
export function mockHuntOverviewPageLocalStore() {
  return mockStore(HuntOverviewPageLocalStore);
}
