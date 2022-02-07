import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiModule} from '../../lib/api/module';
import {newClient} from '../../lib/models/model_test_util';
import {getClientVersions} from '../../store/client_details_diff';
import {ClientDetailsGlobalStore} from '../../store/client_details_global_store';
import {ClientDetailsGlobalStoreMock, mockClientDetailsGlobalStore} from '../../store/client_details_global_store_test_util';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {SelectedClientGlobalStore} from '../../store/selected_client_global_store';
import {initTestEnvironment} from '../../testing';

import {ClientDetails} from './client_details';
import {ClientDetailsModule} from './module';

import {CLIENT_DETAILS_ROUTES} from './routing';


initTestEnvironment();

describe('Client Details Component', () => {
  let store: ClientDetailsGlobalStoreMock;
  let configGlobalStore: ConfigGlobalStoreMock;
  const clientVersionsMock = [
    newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown-changed',
      },
      users: [
        {username: 'foo'},
        {username: 'bar'},
        {username: 'hidden-username'},
      ],
      age: new Date(2020, 2, 1),
    }),
    newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown-first',
      },
      age: new Date(2020, 1, 1),
    }),
  ];

  beforeEach(waitForAsync(() => {
    configGlobalStore = mockConfigGlobalStore();
    store = mockClientDetailsGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientDetailsModule,
            RouterTestingModule.withRoutes(CLIENT_DETAILS_ROUTES),
          ],
          providers: [
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
            {provide: ClientDetailsGlobalStore, useFactory: () => store},
          ],

          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('reads globally selected client id', () => {
    TestBed.createComponent(ClientDetails);
    const selectedClientGlobalStore = TestBed.inject(SelectedClientGlobalStore);

    selectedClientGlobalStore.selectClientId('C.1222');
    expect(store.selectClient).toHaveBeenCalledWith('C.1222');
  });


  it('selects the first option in the timeline by default', () => {
    const fixture = TestBed.createComponent(ClientDetails);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.
    store.mockedObservables.selectedClientVersions$.next(
        getClientVersions(clientVersionsMock));
    fixture.detectChanges();
    const firstOption =
        fixture.debugElement.queryAll(By.css('mat-list-option'))[0];

    expect(firstOption.componentInstance.selected).toBe(true);
  });

  it('getAccordionButtonState() returns the expected state', () => {
    const component = TestBed.createComponent(ClientDetails).componentInstance;

    let totalNumElements = 0;
    let initialMaxNumElements = 0;
    let currentMaxShownElements = 0;
    let state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 0;
    initialMaxNumElements = 1;
    currentMaxShownElements = 0;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 1;
    initialMaxNumElements = 0;
    currentMaxShownElements = 1;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-less');

    totalNumElements = 1;
    initialMaxNumElements = 1;
    currentMaxShownElements = 1;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 1;
    initialMaxNumElements = 2;
    currentMaxShownElements = 1;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 1;
    initialMaxNumElements = 0;
    currentMaxShownElements = 0;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-more');

    totalNumElements = 1;
    initialMaxNumElements = 2;
    currentMaxShownElements = 0;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-more');

    totalNumElements = 3;
    initialMaxNumElements = 2;
    currentMaxShownElements = 0;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-more');

    totalNumElements = 3;
    initialMaxNumElements = 2;
    currentMaxShownElements = 2;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-more');

    totalNumElements = 3;
    initialMaxNumElements = 2;
    currentMaxShownElements = 3;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-less');

    totalNumElements = 3;
    initialMaxNumElements = 3;
    currentMaxShownElements = 3;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 3;
    initialMaxNumElements = 30;
    currentMaxShownElements = 3;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 30;
    initialMaxNumElements = 3;
    currentMaxShownElements = 3;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-more');

    totalNumElements = 30;
    initialMaxNumElements = 3;
    currentMaxShownElements = 30;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('show-less');

    totalNumElements = 30;
    initialMaxNumElements = 30;
    currentMaxShownElements = 30;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 0;
    initialMaxNumElements = 0;
    currentMaxShownElements = 1;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');

    totalNumElements = 0;
    initialMaxNumElements = 1;
    currentMaxShownElements = 1;
    state = component.getAccordionButtonState(
        totalNumElements, currentMaxShownElements, initialMaxNumElements);
    expect(state).toEqual('no-button');
  });

  it('allows expanding and collapsing of lists on button click',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientDetails);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       store.mockedObservables.selectedClientVersions$.next(
           getClientVersions(clientVersionsMock));
       fixture.detectChanges();

       tick();
       fixture.detectChanges();
       let text = fixture.debugElement.nativeElement.textContent;
       expect(text).not.toContain('hidden-username');

       const expandButton = fixture.debugElement.query(By.css('button'));
       expandButton.triggerEventHandler('click', null);
       fixture.detectChanges();
       text = fixture.debugElement.nativeElement.textContent;
       expect(text).toContain('hidden-username');

       const collapseButton = fixture.debugElement.query(By.css('button'));
       collapseButton.triggerEventHandler('click', null);
       fixture.detectChanges();
       text = fixture.debugElement.nativeElement.textContent;
       expect(text).not.toContain('hidden-username');
     }));
});
