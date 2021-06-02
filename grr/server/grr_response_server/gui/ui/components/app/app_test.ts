import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRouteSnapshot, ActivationEnd, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {Subject} from 'rxjs';

import {Writable} from '../../lib/type_utils';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {HomePageGlobalStore} from '../../store/home_page_global_store';
import {mockHomePageGlobalStore} from '../../store/home_page_global_store_test_util';
import {UserGlobalStore} from '../../store/user_global_store';
import {mockUserGlobalStore} from '../../store/user_global_store_test_util';

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
            {provide: ConfigGlobalStore, useFactory: mockConfigGlobalStore},
            {provide: HomePageGlobalStore, useFactory: mockHomePageGlobalStore},
            {provide: UserGlobalStore, useFactory: mockUserGlobalStore},
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
