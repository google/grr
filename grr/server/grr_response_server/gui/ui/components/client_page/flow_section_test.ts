import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiModule} from '../../lib/api/module';
import {newClient} from '../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';
import {Approval} from '../approval/approval';
import {ClientDetailsModule} from '../client_details/module';

import {ClientPageModule} from './client_page_module';
import {FlowSection} from './flow_section';
import {CLIENT_PAGE_ROUTES} from './routing';


initTestEnvironment();

describe('FlowSection', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientPageModule,
            ClientDetailsModule,
            RouterTestingModule.withRoutes(CLIENT_PAGE_ROUTES),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('shows approval if approvalsEnabled$', () => {
    const fixture = TestBed.createComponent(FlowSection);
    fixture.detectChanges();

    injectMockStore(ClientPageGlobalStore)
        .mockedObservables.approvalsEnabled$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.directive(Approval))).not.toBeNull();
  });

  it('does not show approval if approvalsEnabled$ is false', () => {
    const fixture = TestBed.createComponent(FlowSection);
    fixture.detectChanges();

    injectMockStore(ClientPageGlobalStore)
        .mockedObservables.approvalsEnabled$.next(false);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.directive(Approval))).toBeNull();
  });

  it('sends request approval when child approval component emits the info',
     () => {
       const fixture = TestBed.createComponent(FlowSection);
       fixture.detectChanges();
       const client = newClient({
         clientId: 'C.1234',
         ...{},
       });

       const clientPageGlobalStore = injectMockStore(ClientPageGlobalStore);
       clientPageGlobalStore.mockedObservables.approvalsEnabled$.next(true);
       clientPageGlobalStore.mockedObservables.selectedClient$.next(client);
       fixture.detectChanges();

       fixture.debugElement.query(By.directive(Approval))
           .triggerEventHandler('approvalParams', {
             approvers: ['rick', 'jerry'],
             reason: 'sample reason',
             cc: [],
           });
       fixture.detectChanges();

       expect(clientPageGlobalStore.requestApproval).toHaveBeenCalledWith({
         clientId: 'C.1234',
         approvers: ['rick', 'jerry'],
         reason: 'sample reason',
         cc: [],
       });
     });
});
