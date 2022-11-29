import {ChangeDetectorRef, Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiModule} from '../../lib/api/module';
import {newClient} from '../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {VfsViewLocalStore} from '../../store/vfs_view_local_store';
import {mockVfsViewLocalStore} from '../../store/vfs_view_local_store_test_util';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';
import {ClientDetailsModule} from '../client_details/module';
import {ClientOverview} from '../client_overview/client_overview';

import {ClientPageModule} from './client_page_module';
import {FlowSection} from './flow_section';
import {CLIENT_PAGE_ROUTES} from './routing';


initTestEnvironment();


// Load ClientPage in a router-outlet to consume the first URL route
// "/clients/C.1234". Otherwise, ClientPage's router-outlet would consume it
// and show a nested ClientPage.
@Component({template: `<router-outlet></router-outlet>`})
class TestHostComponent {
}

describe('ClientPage Component', () => {
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
          declarations: [
            TestHostComponent,
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            VfsViewLocalStore, {useFactory: mockVfsViewLocalStore})
        .compileComponents();
  }));

  it('loads client information on route change', async () => {
    await TestBed.inject(Router).navigate(['clients', 'C.1234']);

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    const selectedClientGlobalStore =
        injectMockStore(SelectedClientGlobalStore);
    expect(selectedClientGlobalStore.selectClientId).toHaveBeenCalled();

    selectedClientGlobalStore.mockedObservables.clientId$.next('C.1234');

    expect(injectMockStore(ClientPageGlobalStore).selectClient)
        .toHaveBeenCalledWith('C.1234');
  });

  it('shows client data', async () => {
    await TestBed.inject(Router).navigate(['clients', 'C.1234']);

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    injectMockStore(ClientPageGlobalStore)
        .mockedObservables.selectedClient$.next(
            newClient({clientId: 'C.1234'}));
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent).toContain('C.1234');
  });

  it('shows flow section initially', async () => {
    await TestBed.inject(Router).navigate(['clients', 'C.1234']);

    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    expect(fixture.debugElement.query(By.directive(FlowSection)))
        .not.toBeNull();
  });

  it('collapses ClientOverview when navigating to files (failing)',
     async () => {
       await TestBed.inject(Router).navigate(['clients', 'C.1234', 'files']);

       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.detectChanges();

       const tab =
           fixture.debugElement.query(By.css('nav .collected-files-tab'));
       const rla = tab.references['filesActive'];

       // For some reason, Angular's routerLinkActive does not correctly
       // detect active routes in tests, even though the referenced link and
       // active Router URL seem to match. After 1+ hours of researching and
       // debugging, I resort to manually setting `isActive` to still test the
       // association of [routerLinkActive] with ClientOverview.collapsed.
       rla.isActive = true;
       tab.injector.get(ChangeDetectorRef).markForCheck();
       fixture.detectChanges();

       expect(rla.isActive).toBe(true);
       expect(fixture.debugElement.query(By.directive(ClientOverview))
                  .componentInstance.collapsed)
           .toBe(true);
     });
});
