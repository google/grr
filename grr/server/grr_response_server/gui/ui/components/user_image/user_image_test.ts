import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';

import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';

import {UserImageModule} from './module';



initTestEnvironment();

@Component({template: `<user-image [username]="username"></user-image>`})
class TestHostComponent {
  username?: string;
}

describe('UserImage Component', () => {
  let configFacade: ConfigFacadeMock;

  beforeEach(waitForAsync(() => {
    configFacade = mockConfigFacade();

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
            {provide: ConfigFacade, useFactory: () => configFacade},
          ]
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
    configFacade.uiConfigSubject.next(
        {profileImageUrl: 'http://foo/{username}.jpg?sz=123'});
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-icon'))).toBeFalsy();
    const img = fixture.debugElement.query(By.css('img'));
    expect(img).toBeTruthy();
    expect(img.nativeElement.src).toBe('http://foo/test.jpg?sz=123');
  });
});
