import {discardPeriodicTasks, fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {STORE_PROVIDERS} from '../../store/store_test_providers';
import {CLIENT_PAGE_ROUTES} from '../client_page/routing';

import {App} from './app';
import {AppModule} from './app_module';


describe('App Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            AppModule,
            NoopAnimationsModule,
            RouterTestingModule.withRoutes(CLIENT_PAGE_ROUTES),
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
        })
        .compileComponents();
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('should link to the old ui', fakeAsync(async () => {
       const fixture = TestBed.createComponent(App);
       fixture.detectChanges();

       await TestBed.inject(Router).navigate(['/clients/C.123']);
       tick();
       fixture.detectChanges();

       const fallbackLink =
           fixture.debugElement.query(By.css('#fallback-link'));
       expect(fallbackLink.nativeElement.href).toContain('#/clients/C.123');

       discardPeriodicTasks();
     }));
});
