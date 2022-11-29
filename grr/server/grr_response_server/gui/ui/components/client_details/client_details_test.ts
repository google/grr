import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, convertToParamMap, ParamMap} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ReplaySubject} from 'rxjs';

import {ApiModule} from '../../lib/api/module';
import {newClient} from '../../lib/models/model_test_util';
import {getClientVersions} from '../../store/client_details_diff';
import {ClientDetailsGlobalStore} from '../../store/client_details_global_store';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {injectMockStore, STORE_PROVIDERS} from '../../store/store_test_providers';
import {MockStore} from '../../store/store_test_util';
import {DISABLED_TIMESTAMP_REFRESH_TIMER_PROVIDER, initTestEnvironment} from '../../testing';

import {ClientDetails} from './client_details';
import {ClientDetailsModule} from './module';
import {CLIENT_DETAILS_ROUTES} from './routing';


initTestEnvironment();

describe('Client Details Component', () => {
  let store: MockStore<ClientDetailsGlobalStore>;
  let activatedRoute: Partial<ActivatedRoute>&
      {paramMap: ReplaySubject<ParamMap>};

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
      sourceFlowId: '123',
    }),
  ];

  beforeEach(waitForAsync(() => {
    activatedRoute = {
      paramMap: new ReplaySubject<ParamMap>(),
    };

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientDetailsModule,
            RouterTestingModule.withRoutes([
              ...CLIENT_DETAILS_ROUTES,
              // Dummy route to stop error when navigating back to client.
              {path: 'clients/:id', component: ClientDetails},
            ]),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {provide: ActivatedRoute, useFactory: () => activatedRoute},
            DISABLED_TIMESTAMP_REFRESH_TIMER_PROVIDER,
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    store = injectMockStore(ClientDetailsGlobalStore);
  }));

  it('reads client id from URL', () => {
    TestBed.createComponent(ClientDetails);
    activatedRoute.paramMap.next(convertToParamMap({'clientId': 'C.1222'}));
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

  it('selects the entry specified in sourceFlowId route param', () => {
    const fixture = TestBed.createComponent(ClientDetails);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    activatedRoute.paramMap.next(
        convertToParamMap({'clientId': 'C.1234', 'sourceFlowId': '123'}));
    store.mockedObservables.selectedClientVersions$.next(
        getClientVersions(clientVersionsMock));
    fixture.detectChanges();
    const secondOption =
        fixture.debugElement.queryAll(By.css('mat-list-option'))[1];

    expect(secondOption.componentInstance.selected).toBe(true);
  });

  it('shows client fields', fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientDetails);
       fixture.detectChanges();

       store.mockedObservables.selectedClientVersions$.next(getClientVersions([
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'foouser'},
           ],
           osInfo: {
             fqdn: 'foo.f.q.d.n',
           },
           agentInfo: {
             sandboxSupport: true,
             clientBinaryName: 'grr',
           },
           hardwareInfo: {
             systemManufacturer: 'GRR Corp',
           },
           fleetspeakEnabled: true,
           age: new Date(2020, 2, 1),
           sourceFlowId: '123sourceflowid',
         }),
       ]));
       fixture.detectChanges();
       tick();
       fixture.detectChanges();

       expect(fixture.nativeElement.innerText).toContain('foo.f.q.d.n');
       expect(fixture.nativeElement.innerText).toContain('foouser');
       expect(fixture.nativeElement.innerText).toContain('Fleetspeak');
       expect(fixture.nativeElement.innerText).toContain('grr');
       expect(fixture.nativeElement.innerText).toContain('Sandboxing');
       expect(fixture.nativeElement.innerText).toContain('GRR Corp');
       expect(fixture.nativeElement.innerText).toContain('123sourceflowid');
     }));


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

       const expandButton = fixture.debugElement.query(
           By.css('button[name="toggle-users-details"]'));
       expandButton.triggerEventHandler('click', null);
       fixture.detectChanges();
       text = fixture.debugElement.nativeElement.textContent;
       expect(text).toContain('hidden-username');

       const collapseButton = fixture.debugElement.query(
           By.css('button[name="toggle-users-details"]'));
       collapseButton.triggerEventHandler('click', null);
       fixture.detectChanges();
       text = fixture.debugElement.nativeElement.textContent;
       expect(text).not.toContain('hidden-username');
     }));

  it('clicking on interrogate button starts Interrogate configuration',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientDetails);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       store.mockedObservables.selectedClientVersions$.next(
           getClientVersions(clientVersionsMock));
       fixture.detectChanges();
       tick();
       fixture.detectChanges();

       fixture.debugElement.query(By.css('[name="interrogate-button"]'))
           .triggerEventHandler('click', null);

       const clientPageGlobalStore = injectMockStore(ClientPageGlobalStore);
       expect(clientPageGlobalStore.startFlowConfiguration)
           .toHaveBeenCalledOnceWith('Interrogate', {});
       expect(clientPageGlobalStore.scheduleOrStartFlow)
           .toHaveBeenCalledOnceWith({});
     }));
});
