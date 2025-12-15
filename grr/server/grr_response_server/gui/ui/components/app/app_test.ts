import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterModule} from '@angular/router';

import {HttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_test_util';
import {LoadingService} from '../../lib/service/loading_service/loading_service';
import {GlobalStore} from '../../store/global_store';
import {GlobalStoreMock, newGlobalStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {App} from './app';
import {APP_ROUTES} from './routing';
import {AppHarness} from './testing/app_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(App);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    AppHarness,
  );

  return {fixture, harness};
}

describe('App Component', () => {
  let loadingService: LoadingService;
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    loadingService = new LoadingService();
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [
        App,
        NoopAnimationsModule,
        RouterModule.forRoot(APP_ROUTES, {bindToComponentInputs: true}),
      ],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
        {
          provide: LoadingService,
          useValue: loadingService,
        },
      ],
    })
      .overrideComponent(App, {
        set: {
          providers: [
            {
              provide: GlobalStore,
              useValue: globalStoreMock,
            },
          ],
        },
      })
      .compileComponents();
  }));

  it('should be created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.componentInstance).toBeInstanceOf(App);
  });

  it('should initialize global store', async () => {
    await createComponent();

    expect(globalStoreMock.initialize).toHaveBeenCalled();
  });

  it('should show user menu', async () => {
    const {harness} = await createComponent();

    const userMenu = await harness.userMenu();
    expect(userMenu).toBeDefined();
  });

  it('should show loading bar only when loading', async () => {
    const {harness} = await createComponent();

    expect(await harness.isProgressBarVisible()).toBeFalse();

    loadingService.updateLoadingUrls('/foo', true);
    expect(await harness.isProgressBarVisible()).toBeTrue();

    loadingService.updateLoadingUrls('/foo', false);
    expect(await harness.isProgressBarVisible()).toBeFalse();
  });

  describe('navigation tabs', () => {
    it('should open clients page when clicking clients tab', fakeAsync(async () => {
      const {harness} = await createComponent();

      await TestBed.inject(Router).navigate(['/']);

      const tabBar = await harness.tabBar();
      await tabBar.clickLink({label: 'Collect from client'});

      expect(await TestBed.inject(Router).url).toBe('/clients');
    }));

    it('should open fleet collections page when clicking fleet collections tab', fakeAsync(async () => {
      const {harness} = await createComponent();

      await TestBed.inject(Router).navigate(['/']);

      const tabBar = await harness.tabBar();
      await tabBar.clickLink({
        label: 'Collect from fleet',
      });

      expect(await TestBed.inject(Router).url).toBe('/fleet-collections');
    }));

    it('show correct active/inactive state when navigating to "/clients"', fakeAsync(async () => {
      const {harness} = await createComponent();

      await TestBed.inject(Router).navigate(['/clients']);

      const tabBar = await harness.tabBar();
      const activeLink = await tabBar.getActiveLink();
      expect(await activeLink.getLabel()).toBe('Collect from client');
    }));

    it('show correct active/inactive state when navigating to "/fleet-collections"', fakeAsync(async () => {
      const {harness} = await createComponent();

      await TestBed.inject(Router).navigate(['/fleet-collections']);

      const tabBar = await harness.tabBar();
      const activeLink = await tabBar.getActiveLink();
      expect(await activeLink.getLabel()).toBe('Collect from fleet');
    }));

    it('show correct active/inactive state when navigating to "/new-fleet-collection"', fakeAsync(async () => {
      const {harness} = await createComponent();

      await TestBed.inject(Router).navigate(['/new-fleet-collection']);

      const tabBar = await harness.tabBar();
      const activeLink = await tabBar.getActiveLink();
      expect(await activeLink.getLabel()).toBe('Collect from fleet');
    }));
  });
});
