import {Location} from '@angular/common';
import {Component} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {provideRouter} from '@angular/router';

import {STORE_PROVIDERS} from '../../store/store_test_providers';
import {initTestEnvironment} from '../../testing';

import {Home} from './home';
import {HomeModule} from './module';

initTestEnvironment();

@Component({standalone: false, template: '', jit: true})
class TestComponent {}

describe('Home Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [HomeModule, NoopAnimationsModule],
      declarations: [TestComponent],
      providers: [
        ...STORE_PROVIDERS,
        provideRouter([{path: 'clients', component: TestComponent}]),
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
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
