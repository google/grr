import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';
import {initTestEnvironment} from '@app/testing';

import {Home} from './home';
import {HomeModule} from './module';



initTestEnvironment();

describe('Home Component', () => {
  beforeEach(async(() => {
    const router = {navigate: jasmine.createSpy('navigate')};

    TestBed
        .configureTestingModule({
          imports: [
            HomeModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
          ],
          providers: [
            {provide: Router, useValue: router},
          ],

        })
        .compileComponents();
  }));

  it('creates the component', () => {
    const fixture = TestBed.createComponent(Home);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('changes the route when query is submitted', () => {
    const fixture = TestBed.createComponent(Home);
    const componentInstance = fixture.componentInstance;
    componentInstance.onQuerySubmitted('foo');

    const router: Router = TestBed.inject(Router);
    expect(router.navigate).toHaveBeenCalledWith(['v2/client-search', 'foo']);
  });
});
