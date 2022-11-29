import {Location} from '@angular/common';
import {Component} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {STORE_PROVIDERS} from '../../store/store_test_providers';
import {initTestEnvironment} from '../../testing';

import {Home} from './home';
import {HomeModule} from './module';

initTestEnvironment();

@Component({template: ''})
class TestComponent {
}

describe('Home Component', () => {
  beforeEach(waitForAsync(() => {
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
            ...STORE_PROVIDERS,
          ],
          teardown: {destroyAfterEach: false}
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
});
