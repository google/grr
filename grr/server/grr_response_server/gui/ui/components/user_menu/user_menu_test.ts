import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {UserGlobalStore} from '@app/store/user_global_store';
import {initTestEnvironment} from '@app/testing';

import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';

import {UserMenuModule} from './module';

import {UserMenu} from './user_menu';


initTestEnvironment();


describe('UserMenu Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            UserMenuModule,
          ],

          providers: [
            ...STORE_PROVIDERS,
          ],
        })
        .compileComponents();
  }));

  it('displays the current user image', () => {
    const fixture = TestBed.createComponent(UserMenu);
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'test'
    });
    fixture.detectChanges();

    const el = fixture.debugElement.query(By.css('user-image'));
    expect(el).toBeDefined();
    expect(el.componentInstance.username).toBe('test');
  });
});
