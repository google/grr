import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {newClientApproval} from '../../../lib/models/model_test_util';
import {HomePageGlobalStore} from '../../../store/home_page_global_store';
import {RecentClientFlowsLocalStore} from '../../../store/recent_client_flows_local_store';
import {mockRecentClientFlowsLocalStore} from '../../../store/recent_client_flows_local_store_test_util';
import {injectMockStore, STORE_PROVIDERS} from '../../../store/store_test_providers';
import {initTestEnvironment} from '../../../testing';

import {RecentActivityModule} from './module';
import {RecentActivity} from './recent_activity';

initTestEnvironment();

@Component({template: ''})
class DummyComponent {
}

describe('RecentActivity Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            RecentActivityModule,
            RouterTestingModule.withRoutes(
                [{path: 'clients', component: DummyComponent}]),
            NoopAnimationsModule,
          ],
          declarations: [
            DummyComponent,
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
          teardown: {destroyAfterEach: false}
        })
        // The child component RecentClientFlows provides their own Store,
        // needing a super-override in all tests of components that include it.
        .overrideProvider(
            RecentClientFlowsLocalStore,
            {useFactory: mockRecentClientFlowsLocalStore})
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
    injectMockStore(HomePageGlobalStore)
        .mockedObservables.recentClientApprovals$.next([
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
    injectMockStore(HomePageGlobalStore)
        .mockedObservables.recentClientApprovals$.next([
          newClientApproval({status: {type: 'valid'}}),
        ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Access granted');
  });

  it('only shows unique clients in recently accessed clients', () => {
    const fixture = TestBed.createComponent(RecentActivity);
    injectMockStore(HomePageGlobalStore)
        .mockedObservables.recentClientApprovals$.next([
          newClientApproval({clientId: 'C.1111', status: {type: 'valid'}}),
          newClientApproval({
            clientId: 'C.1111',
            status: {type: 'pending', reason: 'Need 1 more approver'}
          })
        ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Access granted');
    expect(text).not.toContain('pending');
  });
});
