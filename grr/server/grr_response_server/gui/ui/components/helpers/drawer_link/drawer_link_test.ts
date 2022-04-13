
import {Component, Input} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';

import {initTestEnvironment} from '../../../testing';

import {DrawerLink} from './drawer_link';
import {DrawerLinkModule} from './drawer_link_module';

initTestEnvironment();

@Component({template: '<a [drawerLink]="drawerLink"></a>'})
class TestHostComponent {
  @Input() drawerLink?: string[];
}

describe('DrawerLink', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            DrawerLinkModule,
            RouterTestingModule.withRoutes([
              {path: 'main', component: TestHostComponent},
              {outlet: 'drawer', path: 'foo', component: TestHostComponent},
            ]),
          ],
          declarations: [
            TestHostComponent,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('is applied on [drawerLink]', async () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    const el = fixture.debugElement.query(By.directive(DrawerLink));
    expect(el).toBeTruthy();
  });

  it('writes link pointing to drawer outlet and allow open new tab',
     async () => {
       const router = TestBed.inject(Router);
       await router.navigate(['main']);

       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.detectChanges();

       fixture.componentInstance.drawerLink = ['foo'];
       fixture.detectChanges();

       // HTML href attribute allows opening the link in a new tab.
       const link = fixture.debugElement.query(By.css('a'));
       expect(link.attributes['href']).toContain('drawer');
       expect(link.attributes['href']).toContain('foo');
     });

  it('navigates with drawer outlet route', fakeAsync(async () => {
       const router = TestBed.inject(Router);
       await router.navigate(['main']);

       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.detectChanges();

       fixture.componentInstance.drawerLink = ['foo'];
       fixture.detectChanges();

       const link = fixture.debugElement.query(By.css('a'));

       link.triggerEventHandler('click', new MouseEvent('click'));
       tick();  // Await Router state change.

       const activeRoutes = router.routerState.root.children;
       expect(activeRoutes.length).toEqual(2);

       expect(urlToString(activeRoutes[0])).toEqual('main');
       expect(activeRoutes[0].outlet).not.toEqual('drawer');

       expect(urlToString(activeRoutes[1])).toEqual('foo');
       expect(activeRoutes[1].outlet).toEqual('drawer');
     }));
});

function urlToString(route: ActivatedRoute) {
  return route.snapshot.url.map(segment => segment.path).join('/');
}
