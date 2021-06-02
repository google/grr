import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ConfigGlobalStore} from '@app/store/config_global_store';
import {UserGlobalStore} from '@app/store/user_global_store';
import {initTestEnvironment} from '@app/testing';

import {mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {mockUserGlobalStore, UserGlobalStoreMock} from '../../store/user_global_store_test_util';

import {UserMenuModule} from './module';

import {UserMenu} from './user_menu';


initTestEnvironment();


describe('UserMenu Component', () => {
  let userGlobalStore: UserGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    userGlobalStore = mockUserGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            UserMenuModule,
          ],

          providers: [
            {provide: UserGlobalStore, useFactory: () => userGlobalStore},
            {provide: ConfigGlobalStore, useFactory: mockConfigGlobalStore}
          ],
        })
        .compileComponents();
  }));

  it('displays the current user image', () => {
    const fixture = TestBed.createComponent(UserMenu);
    userGlobalStore.currentUserSubject.next({name: 'test'});
    fixture.detectChanges();

    const el = fixture.debugElement.query(By.css('user-image'));
    expect(el).toBeDefined();
    expect(el.componentInstance.username).toBe('test');
  });
});
