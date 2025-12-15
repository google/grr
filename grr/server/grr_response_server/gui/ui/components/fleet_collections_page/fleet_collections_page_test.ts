import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Location} from '@angular/common';
import {Signal, signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router, RouterModule} from '@angular/router';

import {ApiListHuntsArgsRobotFilter} from '../../lib/api/api_interfaces';
import {HttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../lib/api/http_api_with_translation_test_util';
import {FlowType} from '../../lib/models/flow';
import {HuntState, ListHuntsArgs} from '../../lib/models/hunt';
import {newGrrUser, newHunt} from '../../lib/models/model_test_util';
import {FleetCollectionsStore} from '../../store/fleet_collections_store';
import {GlobalStore} from '../../store/global_store';
import {
  FleetCollectionsStoreMock,
  GlobalStoreMock,
  newFleetCollectionsStoreMock,
  newGlobalStoreMock,
} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {FLEET_COLLECTION_ROUTES} from '../app/routing';
import {FleetCollectionsPage} from './fleet_collections_page';
import {FleetCollectionsPageHarness} from './testing/fleet_collections_page_harness';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(FleetCollectionsPage);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FleetCollectionsPageHarness,
  );

  return {fixture, harness};
}

describe('Fleet Collections Page Component', () => {
  let fleetCollectionsStoreMock: FleetCollectionsStoreMock;
  let globalStoreMock: GlobalStoreMock;

  beforeEach(waitForAsync(() => {
    fleetCollectionsStoreMock = newFleetCollectionsStoreMock();
    globalStoreMock = newGlobalStoreMock();

    TestBed.configureTestingModule({
      imports: [
        FleetCollectionsPage,
        NoopAnimationsModule,
        RouterModule.forRoot(FLEET_COLLECTION_ROUTES, {
          bindToComponentInputs: true,
        }),
      ],
    })
      .overrideComponent(FleetCollectionsPage, {
        set: {
          providers: [
            {
              provide: FleetCollectionsStore,
              useValue: fleetCollectionsStoreMock,
            },
            {
              provide: GlobalStore,
              useValue: globalStoreMock,
            },
            {
              provide: HttpApiWithTranslationService,
              useValue: mockHttpApiWithTranslationService(),
            },
          ],
        },
      })
      .compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
  });

  it('initially sets the creator filter to NO_ROBOTS', async () => {
    const {harness} = await createComponent();

    const creatorFilterSelect = await harness.getCreatorFilterSelect();
    expect(await creatorFilterSelect.getValueText()).toBe('Created by Humans');
  });

  it('initially sets the state filter no filter', async () => {
    const {harness} = await createComponent();

    const stateFilterSelect = await harness.getStateFilterSelect();
    expect(await stateFilterSelect.getValueText()).toBe('');
  });

  it('initially sets the search filter to an empty string', async () => {
    const {harness} = await createComponent();

    const searchFilterInput = await harness.getSearchFilterInput();
    expect(await searchFilterInput.getValue()).toBe('');
  });

  it('filters for NOT_STARTED fleet collections', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: '1234',
        state: HuntState.NOT_STARTED,
      }),
      newHunt({
        huntId: '5678',
        state: HuntState.REACHED_CLIENT_LIMIT,
      }),
    ]);
    const {harness} = await createComponent();

    const stateFilterSelect = await harness.getStateFilterSelect();
    await stateFilterSelect.clickOptions({text: 'NOT STARTED'});

    const listItems = await harness.getFleetCollectionListItems();
    expect(listItems).toHaveSize(1);
    expect(await harness.getFleetCollectionListItemText(0)).toContain('1234');
  }));

  it('filters for REACHED_CLIENT_LIMIT/PAUSED fleet collections', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: '1234',
        state: HuntState.NOT_STARTED,
      }),
      newHunt({
        huntId: '5678',
        state: HuntState.REACHED_CLIENT_LIMIT,
      }),
    ]);
    const {harness} = await createComponent();

    const stateFilterSelect = await harness.getStateFilterSelect();
    await stateFilterSelect.clickOptions({
      text: 'PAUSED - Reached client limit',
    });

    const listItems = await harness.getFleetCollectionListItems();
    expect(listItems).toHaveSize(1);
    expect(await harness.getFleetCollectionListItemText(0)).toContain('5678');
  }));

  it('searches for fleet collections by description', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: '1234',
        description: 'Banana!',
      }),
      newHunt({
        huntId: '5678',
        description: 'Apple!',
      }),
    ]);
    const {harness} = await createComponent();

    const searchFilterInput = await harness.getSearchFilterInput();
    await searchFilterInput.setValue('Banana');

    const listItems = await harness.getFleetCollectionListItems();
    expect(listItems).toHaveSize(1);
    expect(await harness.getFleetCollectionListItemText(0)).toContain('1234');
  }));

  it('searches for fleet collections by ID', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: '1234',
      }),
      newHunt({
        huntId: '5678',
      }),
    ]);
    const {harness} = await createComponent();

    const searchFilterInput = await harness.getSearchFilterInput();
    await searchFilterInput.setValue('5678');

    const listItems = await harness.getFleetCollectionListItems();
    expect(listItems).toHaveSize(1);
    expect(await harness.getFleetCollectionListItemText(0)).toContain('5678');
  }));

  it('searches for fleet collections by user', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        creator: 'alice',
        huntId: '1234',
      }),
      newHunt({
        creator: 'bob',
        huntId: '5678',
      }),
    ]);
    const {harness} = await createComponent();

    const searchFilterInput = await harness.getSearchFilterInput();
    await searchFilterInput.setValue('alice');

    const listItems = await harness.getFleetCollectionListItems();
    expect(listItems).toHaveSize(1);
    expect(await harness.getFleetCollectionListItemText(0)).toContain('1234');
  }));

  it('calls the store with the initial arguments when the component is created', fakeAsync(async () => {
    let expectedCalls = 0;
    fleetCollectionsStoreMock.pollFleetCollections = ((
      args: Signal<ListHuntsArgs>,
    ) => {
      expect(args()).toEqual({
        count: 100,
        robotFilter: ApiListHuntsArgsRobotFilter.NO_ROBOTS,
        stateFilter: undefined,
      });
      expectedCalls++;
    }) as any; // tslint:disable-line:no-any

    await createComponent();

    expect(expectedCalls).toBe(1);
  }));

  it('displays complete fleet collection item', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: '1234',
        description: 'Banana!',
        creator: 'testuser',
        created: new Date('2024-01-01T00:00:00Z'),
        state: HuntState.NOT_STARTED,
        allClientsCount: BigInt(100),
        completedClientsCount: BigInt(50),
        flowName: 'BananaFlow',
      }),
    ]);
    const {harness} = await createComponent();

    const listItems = await harness.getFleetCollectionListItems();
    expect(listItems).toHaveSize(1);

    expect(await harness.getFleetCollectionListItemTitle(0)).toContain(
      'Banana!',
    );
    const userHarness = await harness.hasFleetCollectionUserHarness(0);
    expect(await userHarness.getTooltipText()).toBe('testuser');
    expect(await harness.getFleetCollectionListItemText(0)).toContain('1234');
    expect(await harness.getFleetCollectionListItemText(0)).toContain(
      '2024-01-01 00:00:00 UTC',
    );
    expect(await harness.getFleetCollectionListItemText(0)).toContain(
      'BananaFlow',
    );
    const progressBar = await harness.getFleetCollectionListItemProgressBar(0);
    expect(await progressBar.getValue()).toBe(50);
    const stateIcon = await harness.getFleetCollectionStateIcon(0);
    const icon = await stateIcon.icon();
    expect(await icon.getName()).toBe('not_started');
  }));

  it('displays several fleet collection items', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({}),
      newHunt({}),
      newHunt({}),
    ]);

    const {harness} = await createComponent();

    const listItems = await harness.getFleetCollectionListItems();
    expect(listItems).toHaveSize(3);
  }));

  it('displays the more fleet collections button when there are more fleet collections', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([newHunt({})]);
    fleetCollectionsStoreMock.hasMoreFleetCollections = signal(true);
    const {harness} = await createComponent();

    const moreFleetCollectionsButton =
      await harness.moreFleetCollectionsButton();
    expect(moreFleetCollectionsButton).not.toBeNull();
  }));

  it('does not display the more fleet collections button when there are no more fleet collections', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([newHunt({})]);
    fleetCollectionsStoreMock.hasMoreFleetCollections = signal(false);
    const {harness} = await createComponent();

    const moreFleetCollectionsButton =
      await harness.moreFleetCollectionsButton();
    expect(moreFleetCollectionsButton).toBeNull();
  }));

  it('clicking on the fleet collection item navigates to the fleet collection', fakeAsync(async () => {
    await TestBed.inject(Router).navigate(['/fleet-collections']);

    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({huntId: '1234'}),
    ]);
    const {harness} = await createComponent();

    const listItems = await harness.getFleetCollectionListItems();
    const itemHost = await listItems[0].host();
    await itemHost.click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual('/fleet-collections/1234/results');
  }));

  it('displays the fleet collection menu button', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([newHunt({})]);
    const {harness} = await createComponent();

    const menuButton = await harness.getFleetCollectionMenuButton(0);
    await menuButton.click();
    const menuItems = await harness.getFleetCollectionMenuItems(0);
    expect(menuItems).toHaveSize(1);
    expect(await menuItems[0].getText()).toContain(
      'Duplicate fleet collection',
    );
  }));

  it('disables the duplicate fleet collection menu item for restricted flows', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(
      newGrrUser({
        isAdmin: false,
      }),
    );
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: 'ABCD1234',
        flowType: FlowType.EXECUTE_PYTHON_HACK,
      }),
    ]);
    const {harness} = await createComponent();

    const menuItem = await harness.getFleetCollectionDuplicateMenuItem(0);
    expect(await menuItem.isDisabled()).toBeTrue();
  }));

  it('enables the duplicate fleet collection menu item for non-restricted flows', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(
      newGrrUser({
        isAdmin: false,
      }),
    );
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: 'ABCD1234',
        flowType: FlowType.STAT_MULTIPLE_FILES,
      }),
    ]);
    const {harness} = await createComponent();

    const menuItem = await harness.getFleetCollectionDuplicateMenuItem(0);
    expect(await menuItem.isDisabled()).toBeFalse();
  }));

  it('enables the duplicate fleet collection menu item for admin users', fakeAsync(async () => {
    globalStoreMock.currentUser = signal(
      newGrrUser({
        isAdmin: true,
      }),
    );
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: 'ABCD1234',
        flowType: FlowType.EXECUTE_PYTHON_HACK,
      }),
    ]);
    const {harness} = await createComponent();

    const menuItem = await harness.getFleetCollectionDuplicateMenuItem(0);
    expect(await menuItem.isDisabled()).toBeFalse();
  }));

  it('clicking on the duplicate fleet collection menu item navigates to the new fleet collection page', fakeAsync(async () => {
    fleetCollectionsStoreMock.fleetCollections = signal([
      newHunt({
        huntId: 'ABCD1234',
      }),
    ]);
    const {harness} = await createComponent();

    const menuButton = await harness.getFleetCollectionMenuButton(0);
    await menuButton.click();
    const menuItems = await harness.getFleetCollectionMenuItems(0);
    await menuItems[0].click();

    const location = TestBed.inject(Location);
    expect(location.path()).toEqual(
      '/new-fleet-collection?fleetCollectionId=ABCD1234',
    );
  }));
});
