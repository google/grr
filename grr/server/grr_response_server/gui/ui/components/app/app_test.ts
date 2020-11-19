import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRouteSnapshot, ActivationEnd, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {Subject} from 'rxjs';

import {Writable} from '../../lib/type_utils';
import {ConfigFacade} from '../../store/config_facade';
import {mockConfigFacade} from '../../store/config_facade_test_util';
import {HomePageFacade} from '../../store/home_page_facade';
import {mockHomePageFacade} from '../../store/home_page_facade_test_util';
import {UserFacade} from '../../store/user_facade';
import {mockUserFacade} from '../../store/user_facade_test_util';

import {App} from './app';
import {AppModule} from './app_module';



describe('App Component', () => {
  let routerEvents: Subject<ActivationEnd>;

  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            AppModule,
            NoopAnimationsModule,
            RouterTestingModule,
          ],

          providers: [
            {provide: ConfigFacade, useFactory: mockConfigFacade},
            {provide: HomePageFacade, useFactory: mockHomePageFacade},
            {provide: UserFacade, useFactory: mockUserFacade},
          ],
        })
        .compileComponents();

    routerEvents = new Subject();
    const router = TestBed.inject(Router);
    (router as Writable<Router>).events = routerEvents.asObservable();
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('should link to the old ui', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const snapshot = new ActivatedRouteSnapshot();
    snapshot.params = {id: 'C.1234'};
    snapshot.queryParams = {};
    snapshot.data = {legacyLink: '#/legacy/:id/foo'};
    routerEvents.next(new ActivationEnd(snapshot));

    fixture.detectChanges();

    const fallbackLink = fixture.debugElement.query(By.css('#fallback-link'));
    expect(fallbackLink.nativeElement.href).toContain('#/legacy/C.1234/foo');
  });
});
