import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';

import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock, newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {APP_ROUTES} from '../app/routing';
import {NotFoundPage} from './not_found_page';
import {NotFoundPageHarness} from './testing/not_found_page_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(NotFoundPage);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    NotFoundPageHarness,
  );

  return {fixture, harness};
}

describe('Not Found Page Component', () => {
  let globalStoreMock: GlobalStoreMock;
  let mockWindow = {location: {href: ''}};

  beforeEach(waitForAsync(() => {
    globalStoreMock = newGlobalStoreMock();
    mockWindow = {
      location: {
        href: '',
      },
    };

    TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        NotFoundPage,
        RouterModule.forRoot(APP_ROUTES),
      ],
      providers: [
        {
          provide: GlobalStore,
          useValue: globalStoreMock,
        },
        {
          provide: 'Window',
          useValue: mockWindow,
        },
      ],
    }).compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.componentInstance).toBeInstanceOf(NotFoundPage);
  });

  it('should show version and address', async () => {
    globalStoreMock.uiConfig = signal({
      grrVersion: '0.0.0',
    });
    const {harness} = await createComponent();

    const text = await (await harness.host()).text();
    expect(text).toContain('Version: 0.0.0');
    expect(text).toContain('Address: /');
  });

  it('should navigate back when back button is clicked', async () => {
    spyOn(window.history, 'back');
    const {harness} = await createComponent();

    await (await harness.backButton()).click();
    expect(window.history.back).toHaveBeenCalled();
  });

  it('should open report URL when report button is clicked', async () => {
    globalStoreMock.uiConfig = signal({
      reportUrl: 'https://example.com/report',
    });
    const {harness} = await createComponent();

    const reportButton = await harness.reportButton();
    expect(await (await reportButton.host()).getProperty('href')).toBe(
      'https://example.com/report',
    );
  });
});
