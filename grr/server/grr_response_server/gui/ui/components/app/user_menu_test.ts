import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {newGrrUser} from '../../lib/models/model_test_util';
import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock, newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {UserMenuHarness} from './testing/user_menu_harness';
import {UserMenu} from './user_menu';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(UserMenu);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    UserMenuHarness,
  );

  return {fixture, harness};
}

describe('User Menu Component', () => {
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, UserMenu],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
      ],
    }).compileComponents();
  }));

  afterEach(() => {
    window.localStorage.clear();
  });

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.componentInstance).toBeInstanceOf(UserMenu);
  });

  it('displays button and the menu', async () => {
    globalStoreMock.currentUser = signal(newGrrUser({name: 'test'}));
    const {harness} = await createComponent();

    const button = await harness.userButton();
    expect(button).toBeDefined();
    const menuItems = await harness.getMenuItems();
    expect(menuItems.length).toBe(2);
    expect(await menuItems[0].getText()).toContain('User:');
    expect(await menuItems[0].getText()).toContain('Admin:');
    expect(await menuItems[1].getText()).toBe('Dark mode');
  });

  it('shows user information', async () => {
    globalStoreMock.currentUser = signal(
      newGrrUser({name: 'testuser', isAdmin: true}),
    );
    const {harness} = await createComponent();

    const button = await harness.userButton();
    await button!.click();

    const userInfo = await harness.getMenuItem(0);
    expect(await userInfo.getText()).toContain('User:');
    expect(await userInfo.getText()).toContain('testuser');
    expect(await userInfo.getText()).toContain('Admin:');
    expect(await userInfo.getText()).toContain('YES');
  });

  it('is set to light mode by default', async () => {
    const {fixture} = await createComponent();

    expect(fixture.debugElement.query(By.css('.dark-mode'))).toBeNull();
  });

  it('initializes dark mode from local storage', async () => {
    window.localStorage.setItem('darkMode', 'true');
    const {fixture} = await createComponent();

    expect(fixture.debugElement.query(By.css('.dark-mode'))).toBeDefined();
  });

  it('dark mode toggle updates dark mode settings', async () => {
    globalStoreMock.currentUser = signal(newGrrUser({name: 'test'}));

    const {harness, fixture} = await createComponent();

    const button = await harness.userButton();
    await button!.click();
    const menu = await harness.menu();
    expect(menu).toBeDefined();
    const darkModeMenuItem = await harness.getMenuItem(1);
    await darkModeMenuItem.click();

    expect(fixture.debugElement.query(By.css('.dark-mode'))).toBeNull();
  });
});
