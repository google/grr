import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {UserHarness} from './testing/user_harness';
import {User} from './user';

initTestEnvironment();

async function createComponent(withName = false) {
  const fixture = TestBed.createComponent(User);
  // Set the default value here as the input is required.
  fixture.componentRef.setInput('username', 'testuser');
  fixture.componentRef.setInput('withName', withName);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    UserHarness,
  );
  return {fixture, harness};
}

describe('User Component', () => {
  const globalStore: GlobalStoreMock = {
    uiConfig: signal(null),
  };

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [User, NoopAnimationsModule],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStore,
        },
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('displays a fallback image when profileImageUrl is not set ', fakeAsync(async () => {
    globalStore.uiConfig = signal(null);
    tick();

    const {harness} = await createComponent();
    expect(await harness.hasFallbackIcon()).toBeTrue();
    expect(await harness.hasProfileImage()).toBeFalse();
  }));

  it('displays the profile image ', fakeAsync(async () => {
    globalStore.uiConfig = signal({
      profileImageUrl: 'http://foo/{username}.jpg?sz=123',
    });
    tick();

    const {harness, fixture} = await createComponent();
    fixture.componentRef.setInput('username', 'FooBar');

    expect(await harness.hasFallbackIcon()).toBeFalse();
    expect(await harness.hasProfileImage()).toBeTrue();
    expect(await harness.getImageSrc()).toBe('http://foo/FooBar.jpg?sz=123');
  }));

  it('displays the username if withName is true', fakeAsync(async () => {
    const {harness} = await createComponent(true);
    expect(await harness.hasUsername()).toBeTrue();
    expect(await harness.getUsername()).toBe('testuser');
  }));

  it('does not display the username if withName is false', fakeAsync(async () => {
    const {harness} = await createComponent(false);
    expect(await harness.hasUsername()).toBeFalse();
  }));
});
