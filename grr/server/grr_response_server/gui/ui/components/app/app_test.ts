import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRouteSnapshot, ActivationEnd, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {Subject} from 'rxjs';

import {Writable} from '../../lib/type_utils';
import {STORE_PROVIDERS} from '../../store/store_test_providers';

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
            ...STORE_PROVIDERS,
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

    const snapshot: Partial<ActivatedRouteSnapshot> = {
      params: {id: 'C.1234'},
      queryParams: {},
      data: {legacyLink: '#/legacy/:id/foo'},
      children: [],
    };

    routerEvents.next(new ActivationEnd(snapshot as ActivatedRouteSnapshot));

    fixture.detectChanges();

    const fallbackLink = fixture.debugElement.query(By.css('#fallback-link'));
    expect(fallbackLink.nativeElement.href).toContain('#/legacy/C.1234/foo');
  });
});
