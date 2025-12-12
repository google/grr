import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

import {HttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_service';
import {
  HttpApiWithTranslationServiceMock,
  mockHttpApiWithTranslationService,
} from '../../lib/api/http_api_with_translation_test_util';
import {ClientStore} from '../../store/client_store';
import {ClientStoreMock, newClientStoreMock} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {CLIENT_ROUTES} from '../app/routing';
import {ClientHistory} from './client_history/client_history';
import {ClientPage} from './client_page';
import {ClientPageHarness} from './testing/client_page_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(ClientPage);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    ClientPageHarness,
  );

  return {fixture, harness};
}

describe('Client Page Component', () => {
  let httpApiService: HttpApiWithTranslationServiceMock;
  let clientStoreMock: ClientStoreMock;

  beforeEach(waitForAsync(() => {
    httpApiService = mockHttpApiWithTranslationService();
    clientStoreMock = {
      initialize: jasmine.createSpy('initialize'),
      ...newClientStoreMock(),
    };

    TestBed.configureTestingModule({
      imports: [
        ClientPage,
        ClientHistory,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useFactory: () => httpApiService,
        },
      ],
      teardown: {destroyAfterEach: false},
    })
      .overrideComponent(ClientPage, {
        set: {
          providers: [
            {
              provide: ClientStore,
              useValue: clientStoreMock,
            },
          ],
        },
      })
      .compileComponents();
  }));

  it('initializes ClientStore', async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/clients/C.1222', ClientPage);

    expect(clientStoreMock.initialize).toHaveBeenCalledWith('C.1222');
  });

  it('displays ClientOverview', fakeAsync(async () => {
    const {harness} = await createComponent();
    expect(await harness.getClientOverviewHarness()).toBeDefined();
  }));

  it('shows nav bar with all tabs', fakeAsync(async () => {
    const {harness} = await createComponent();
    const tabBar = await harness.getTabNavBar();
    const tabLinks = await tabBar.getLinks();
    expect(tabLinks.length).toBe(4);
    expect(await tabLinks[0].getLabel()).toBe('Flows');
    expect(await tabLinks[1].getLabel()).toBe('Client History');
    expect(await tabLinks[2].getLabel()).toBe('Approvals');
    expect(await tabLinks[3].getLabel()).toBe(
      'Browse collected files & metadata',
    );
  }));

  it('shows nav bar with enabled files tab if user has access', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(true);
    const {harness} = await createComponent();

    const tabBar = await harness.getTabNavBar();
    const tabLinks = await tabBar.getLinks({
      label: 'Browse collected files & metadata',
    });

    expect(await tabLinks[0].isDisabled()).toBeFalse();
  }));

  it('shows nav bar with disabled files tab if user has no access', fakeAsync(async () => {
    clientStoreMock.hasAccess = signal(false);
    const {harness} = await createComponent();

    const tabBar = await harness.getTabNavBar();
    const tabLinks = await tabBar.getLinks({
      label: 'Browse collected files & metadata',
    });

    expect(await tabLinks[0].isDisabled()).toBeTrue();
  }));

  it('navigation to /clients/C.1222/history opens History tab in router outlet', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/clients/C.1222/history');

    const {harness} = await createComponent();
    expect(await harness.isClientHistoryVisible()).toBeTrue();
  }));

  it('navigation to /clients/C.1222/flows opens Flows tab in router outlet', fakeAsync(async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl('/clients/C.1222/flows');

    const {harness} = await createComponent();
    expect(await harness.isClientFlowsVisible()).toBeTrue();
  }));
});
