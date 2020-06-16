import {async, TestBed} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {GrrUser} from '@app/lib/models/user';
import {UserFacade} from '@app/store/user_facade';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

import {UserMenu} from './user_menu';


initTestEnvironment();


describe('UserMenu Component', () => {
  let currentUser$: Subject<GrrUser>;
  let userFacade: Partial<UserFacade>;

  beforeEach(async(() => {
    currentUser$ = new Subject();
    userFacade = {
      currentUser$,
    };

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
          ],

          providers: [{provide: UserFacade, useValue: userFacade}]
        })
        .compileComponents();
  }));

  it('displays the current user name', () => {
    const fixture = TestBed.createComponent(UserMenu);
    fixture.detectChanges();

    currentUser$.next({
      name: 'test',
    });
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('test');
  });
});
