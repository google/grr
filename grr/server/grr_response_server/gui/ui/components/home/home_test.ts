import {Location} from '@angular/common';
import {Component} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';
import {initTestEnvironment} from '@app/testing';

import {newClientApproval} from '../../lib/models/model_test_util';
import {ConfigFacade} from '../../store/config_facade';
import {mockConfigFacade} from '../../store/config_facade_test_util';
import {HomePageFacade} from '../../store/home_page_facade';
import {HomePageFacadeMock, mockHomePageFacade} from '../../store/home_page_facade_test_util';

import {Home} from './home';
import {HomeModule} from './module';



initTestEnvironment();

@Component({template: ''})
class TestComponent {
}

describe('Home Component', () => {
  let homePageFacade: HomePageFacadeMock;

  beforeEach(waitForAsync(() => {
    homePageFacade = mockHomePageFacade();

    TestBed
        .configureTestingModule({
          imports: [
            RouterTestingModule.withRoutes(
                [{path: 'clients', component: TestComponent}]),
            HomeModule,
            NoopAnimationsModule,
          ],
          declarations: [
            TestComponent,
          ],
          providers: [
            {provide: HomePageFacade, useFactory: () => homePageFacade},
            {provide: ConfigFacade, useFactory: mockConfigFacade},
          ],

        })
        .compileComponents();
  }));

  it('creates the component', () => {
    const fixture = TestBed.createComponent(Home);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('changes the route when query is submitted', fakeAsync(() => {
       const fixture = TestBed.createComponent(Home);
       const componentInstance = fixture.componentInstance;
       componentInstance.onQuerySubmitted('foo');
       tick();

       const location = TestBed.inject(Location);
       expect(location.path()).toEqual('/clients?q=foo');
     }));

  it('displays recently accessed clients', () => {
    const fixture = TestBed.createComponent(Home);
    homePageFacade.recentClientApprovalsSubject.next([
      newClientApproval({clientId: 'C.1111', status: {type: 'valid'}}),
      newClientApproval({clientId: 'C.2222', status: {type: 'valid'}}),
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1111');
    expect(text).toContain('C.2222');
  });
});
