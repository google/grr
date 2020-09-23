import {async, TestBed} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ConfigFacade} from '@app/store/config_facade';
import {UserFacade} from '@app/store/user_facade';
import {initTestEnvironment} from '@app/testing';

import {mockConfigFacade} from '../../store/config_facade_test_util';
import {mockUserFacade, UserFacadeMock} from '../../store/user_facade_test_util';

import {UserMenuModule} from './module';

import {UserMenu} from './user_menu';


initTestEnvironment();


describe('UserMenu Component', () => {
  let userFacade: UserFacadeMock;

  // TODO(user): Change to waitForAsync once we run on Angular 10, which
  //  in turn requires TypeScript 3.9.
  // tslint:disable-next-line:deprecation
  beforeEach(async(() => {
    userFacade = mockUserFacade();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            UserMenuModule,
          ],

          providers: [
            {provide: UserFacade, useFactory: () => userFacade},
            {provide: ConfigFacade, useFactory: mockConfigFacade}
          ],
        })
        .compileComponents();
  }));

  it('displays the current user image', () => {
    const fixture = TestBed.createComponent(UserMenu);
    userFacade.currentUserSubject.next({name: 'test'});
    fixture.detectChanges();

    const el = fixture.debugElement.query(By.css('user-image'));
    expect(el).toBeDefined();
    expect(el.componentInstance.username).toBe('test');
  });
});
