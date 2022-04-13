import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {UserGlobalStore} from '../../store/user_global_store';
import {initTestEnvironment} from '../../testing';

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
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('displays the current user image', () => {
    const fixture = TestBed.createComponent(UserMenu);
    injectMockStore(UserGlobalStore).mockedObservables.currentUser$.next({
      name: 'test',
      canaryMode: false,
      huntApprovalRequired: false,
    });
    fixture.detectChanges();

    const el = fixture.debugElement.query(By.css('user-image'));
    expect(el).toBeDefined();
    expect(el.componentInstance.username).toBe('test');
  });
});
