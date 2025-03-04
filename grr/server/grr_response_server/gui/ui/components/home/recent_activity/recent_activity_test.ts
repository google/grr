import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {provideRouter} from '@angular/router';

import {newClientApproval} from '../../../lib/models/model_test_util';
import {HomePageGlobalStore} from '../../../store/home_page_global_store';
import {RecentClientFlowsLocalStore} from '../../../store/recent_client_flows_local_store';
import {
  mockRecentClientFlowsLocalStore,
  RecentClientFlowsLocalStoreMock,
} from '../../../store/recent_client_flows_local_store_test_util';
import {
  injectMockStore,
  STORE_PROVIDERS,
} from '../../../store/store_test_providers';
import {initTestEnvironment} from '../../../testing';

import {RecentActivityModule} from './module';
import {RecentActivity} from './recent_activity';

initTestEnvironment();

@Component({standalone: false, template: '', jit: true})
class DummyComponent {}

describe('RecentActivity Component', () => {
  let recentClientFlowsLocalStore: RecentClientFlowsLocalStoreMock;

  beforeEach(waitForAsync(() => {
    recentClientFlowsLocalStore = mockRecentClientFlowsLocalStore();

    TestBed.configureTestingModule({
      imports: [RecentActivityModule, NoopAnimationsModule],
      declarations: [DummyComponent],
      providers: [
        ...STORE_PROVIDERS,
        provideRouter([{path: 'clients', component: DummyComponent}]),
      ],
      teardown: {destroyAfterEach: false},
    })
      // The child component RecentClientFlows provides their own Store,
      // needing a super-override in all tests of components that include it.
      .overrideProvider(RecentClientFlowsLocalStore, {
        useFactory: () => recentClientFlowsLocalStore,
      })
      .compileComponents();
  }));

  it('renders title when loaded', () => {
    const fixture = TestBed.createComponent(RecentActivity);
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Recent activity');
  });

  it('displays recently accessed clients', () => {
    const fixture = TestBed.createComponent(RecentActivity);
    injectMockStore(
      HomePageGlobalStore,
    ).mockedObservables.recentClientApprovals$.next([
      newClientApproval({clientId: 'C.1111', status: {type: 'valid'}}),
      newClientApproval({clientId: 'C.2222', status: {type: 'valid'}}),
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1111');
    expect(text).toContain('C.2222');
  });

  it('shows approval information for recently accessed clients', () => {
    const fixture = TestBed.createComponent(RecentActivity);
    injectMockStore(
      HomePageGlobalStore,
    ).mockedObservables.recentClientApprovals$.next([
      newClientApproval({status: {type: 'valid'}}),
    ]);
    recentClientFlowsLocalStore.mockedObservables.hasAccess$.next(true);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Access granted');
  });

  it('only shows unique clients in recently accessed clients', () => {
    const fixture = TestBed.createComponent(RecentActivity);
    injectMockStore(
      HomePageGlobalStore,
    ).mockedObservables.recentClientApprovals$.next([
      newClientApproval({clientId: 'C.1111', status: {type: 'valid'}}),
      newClientApproval({
        clientId: 'C.1111',
        status: {type: 'pending', reason: 'Need 1 more approver'},
      }),
    ]);
    recentClientFlowsLocalStore.mockedObservables.hasAccess$.next(true);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Access granted');
    expect(text).not.toContain('pending');
  });
});
