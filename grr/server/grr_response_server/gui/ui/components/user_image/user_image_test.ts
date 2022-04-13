import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../testing';

import {UserImageModule} from './module';


initTestEnvironment();

@Component({template: `<user-image [username]="username"></user-image>`})
class TestHostComponent {
  username?: string;
}

describe('UserImage Component', () => {
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            UserImageModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('displays a fallback image when profileImageUrl is not configured ',
     () => {
       const fixture = TestBed.createComponent(TestHostComponent);
       fixture.componentInstance.username = 'test';
       fixture.detectChanges();

       expect(fixture.debugElement.query(By.css('mat-icon'))).toBeTruthy();
       expect(fixture.debugElement.query(By.css('img'))).toBeFalsy();
     });

  it('displays the profile image ', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.username = 'test';
    configGlobalStore.mockedObservables.uiConfig$.next(
        {profileImageUrl: 'http://foo/{username}.jpg?sz=123'});
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-icon'))).toBeFalsy();
    const img = fixture.debugElement.query(By.css('img'));
    expect(img).toBeTruthy();
    expect(img.nativeElement.src).toBe('http://foo/test.jpg?sz=123');
  });
});
