import {DebugElement} from '@angular/core';
import {ComponentFixture, discardPeriodicTasks, fakeAsync, flush, TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';

import {HttpApiService} from '../../lib/api/http_api_service';
import {mockHttpApiService} from '../../lib/api/http_api_service_test_util';
import {MetricsService, UiRedirectDirection, UiRedirectSource} from '../../lib/service/metrics_service/metrics_service';
import {STORE_PROVIDERS} from '../../store/store_test_providers';

import {App} from './app';
import {AppModule} from './app_module';

function getNavTab<Component>(
    fixture: ComponentFixture<Component>, route: string): DebugElement|
    undefined {
  const navTabs = fixture.debugElement.queryAll(By.css(`nav.app-navigation
  a`));

  return navTabs.find(item => item.nativeElement.href.endsWith(route));
}

describe('App Component', () => {
  let metricsService: Partial<MetricsService>;

  beforeEach(waitForAsync(() => {
    metricsService = {
      registerUIRedirect: jasmine.createSpy('registerUIRedirect'),
    };

    TestBed
        .configureTestingModule({
          imports: [
            AppModule,
            NoopAnimationsModule,
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: HttpApiService, useFactory: () => mockHttpApiService()},
          ],
        })
        .overrideProvider(MetricsService, {useFactory: () => metricsService})
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
       flush();
       fixture.detectChanges();

       const fallbackLink =
           fixture.debugElement.query(By.css('#fallback-link'));
       expect(fallbackLink.nativeElement.href).toContain('#/clients/C.123');

       discardPeriodicTasks();
     }));

  it('button click handler calls metrics service', fakeAsync(async () => {
       const fixture = TestBed.createComponent(App);
       fixture.detectChanges();

       // We avoid clicking the link so the window will not reload during the
       // test execution.
       fixture.componentInstance.registerRedirect();

       expect(metricsService.registerUIRedirect)
           .toHaveBeenCalledWith(
               UiRedirectDirection.NEW_TO_OLD,
               UiRedirectSource.REDIRECT_BUTTON);

       discardPeriodicTasks();
     }));

  describe('Navigation tabs', () => {
    it('should point to right pages', fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/']);
         fixture.detectChanges();

         flush();
         fixture.detectChanges();

         const navLinks =
             fixture.debugElement.queryAll(By.css('nav.app-navigation a'));
         expect(navLinks.length).toBe(2);
         expect(navLinks[0].nativeElement.href)
             .toMatch(/.*\/$/);  // ends in `/`
         expect(navLinks[1].nativeElement.href)
             .toMatch(/.*\/hunts$/);  // ends in `/hunts`

         discardPeriodicTasks();
       }));

    it('navbar should redirect to right pages', fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/']);
         flush();
         fixture.detectChanges();

         const navLinks =
             fixture.debugElement.queryAll(By.css('nav.app-navigation a'));
         expect(navLinks.length).toBe(2);
         expect(navLinks[0].nativeElement.href)
             .toMatch(/.*\/$/);  // ends in `/`

         expect(navLinks[0].attributes['class'])
             .toContain('mat-tab-label-active');
         expect(navLinks[1].attributes['class'])
             .not.toContain('mat-tab-label-active');

         expect(navLinks[1].nativeElement.href)
             .toMatch(/.*\/hunts$/);  // ends in `/hunts`
         navLinks[1].nativeElement.click();
         flush();
         fixture.detectChanges();

         expect(navLinks[0].attributes['class'])
             .not.toContain('mat-tab-label-active');
         expect(navLinks[1].attributes['class'])
             .toContain('mat-tab-label-active');

         discardPeriodicTasks();
       }));

    it('show correct active/inactive state when navigating to "/"',
       fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/']);
         flush();
         fixture.detectChanges();

         const clientsNavTab = getNavTab(fixture, '/');
         expect(clientsNavTab).toBeDefined();
         expect(clientsNavTab!.attributes['class'])
             .toContain('mat-tab-label-active');

         const huntsNavTab = getNavTab(fixture, '/hunts');
         expect(huntsNavTab).toBeDefined();
         expect(huntsNavTab!.attributes['class'])
             .not.toContain('mat-tab-label-active');

         discardPeriodicTasks();
       }));

    it('show correct active/inactive state when navigating to "/clients"',
       fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/clients']);
         flush();
         fixture.detectChanges();

         const clientsNavTab = getNavTab(fixture, '/');
         expect(clientsNavTab).toBeDefined();
         expect(clientsNavTab!.attributes['class'])
             .toContain('mat-tab-label-active');

         const huntsNavTab = getNavTab(fixture, '/hunts');
         expect(huntsNavTab).toBeDefined();
         expect(huntsNavTab!.attributes['class'])
             .not.toContain('mat-tab-label-active');

         discardPeriodicTasks();
       }));

    it('show correct active/inactive state when navigating to "/clients/C.1234"',
       fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/clients/C.1234']);
         flush();
         fixture.detectChanges();

         const clientsNavTab = getNavTab(fixture, '/');
         expect(clientsNavTab).toBeDefined();
         expect(clientsNavTab!.attributes['class'])
             .toContain('mat-tab-label-active');

         const huntsNavTab = getNavTab(fixture, '/hunts');
         expect(huntsNavTab).toBeDefined();
         expect(huntsNavTab!.attributes['class'])
             .not.toContain('mat-tab-label-active');

         discardPeriodicTasks();
       }));

    it('show correct active/inactive state when navigating to "/hunts"',
       fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/hunts']);
         flush();
         fixture.detectChanges();

         const clientsNavTab = getNavTab(fixture, '/');
         expect(clientsNavTab).toBeDefined();
         expect(clientsNavTab!.attributes['class'])
             .not.toContain('mat-tab-label-active');

         const huntsNavTab = getNavTab(fixture, '/hunts');
         expect(huntsNavTab).toBeDefined();
         expect(huntsNavTab!.attributes['class'])
             .toContain('mat-tab-label-active');

         discardPeriodicTasks();
       }));

    it('show correct active/inactive state when navigating to "/hunts/123ABCD4"',
       fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/hunts/1234ABCD']);
         flush();
         fixture.detectChanges();

         const clientsNavTab = getNavTab(fixture, '/');
         expect(clientsNavTab).toBeDefined();
         expect(clientsNavTab!.attributes['class'])
             .not.toContain('mat-tab-label-active');

         const huntsNavTab = getNavTab(fixture, '/hunts');
         expect(huntsNavTab).toBeDefined();
         expect(huntsNavTab!.attributes['class'])
             .toContain('mat-tab-label-active');

         discardPeriodicTasks();
       }));

    it('show correct active/inactive state when navigating to "/approvals"',
       fakeAsync(async () => {
         const fixture = TestBed.createComponent(App);
         fixture.detectChanges();

         await TestBed.inject(Router).navigate(['/approvals']);
         flush();
         fixture.detectChanges();

         const clientsNavTab = getNavTab(fixture, '/');
         expect(clientsNavTab).toBeDefined();
         expect(clientsNavTab!.attributes['class'])
             .not.toContain('mat-tab-label-active');

         const huntsNavTab = getNavTab(fixture, '/hunts');
         expect(huntsNavTab).toBeDefined();
         expect(huntsNavTab!.attributes['class'])
             .not.toContain('mat-tab-label-active');

         discardPeriodicTasks();
       }));
  });
});
