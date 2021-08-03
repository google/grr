import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ApiModule} from '@app/lib/api/module';

import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {getActivatedChildRoute, initTestEnvironment} from '../../testing';
import {ClientDetailsModule} from '../client_details/module';

import {ClientPage as ClientComponent} from './client_page';
import {ClientPageModule} from './module';

import {CLIENT_PAGE_ROUTES} from './routing';


initTestEnvironment();

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
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: getActivatedChildRoute},
          ],

        })
        .compileComponents();
  }));

  it('loads client information on route change', async () => {
    await TestBed.inject(Router).navigate(['clients', 'C.1234']);

    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    const selectedClientGlobalStore =
        injectMockStore(SelectedClientGlobalStore);
    expect(selectedClientGlobalStore.selectClientId).toHaveBeenCalled();

    selectedClientGlobalStore.mockedObservables.clientId$.next('C.1234');

    expect(injectMockStore(ClientPageGlobalStore).selectClient)
        .toHaveBeenCalledWith('C.1234');
  });

  it('shows approval iff approvalsEnabled$', () => {
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();

    injectMockStore(ClientPageGlobalStore)
        .mockedObservables.approvalsEnabled$.next(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.client-approval'))
               .styles['display'])
        .toEqual('block');
  });

  it('does not show approval if approvalsEnabled$ is false', () => {
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();

    injectMockStore(ClientPageGlobalStore)
        .mockedObservables.approvalsEnabled$.next(false);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('.client-approval'))
               .styles['display'])
        .toEqual('none');
  });
});
