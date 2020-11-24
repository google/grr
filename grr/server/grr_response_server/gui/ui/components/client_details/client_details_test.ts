import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Router} from '@angular/router';
import {Subject} from 'rxjs';

import {ApiModule} from '../../lib/api/module';
import {Client} from '../../lib/models/client';
import {newClient} from '../../lib/models/model_test_util';
import {ClientVersion, getClientVersions} from '../../store/client_details_diff';
import {ClientDetailsFacade} from '../../store/client_details_facade';
import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';
import {initTestEnvironment} from '../../testing';

import {ClientDetails} from './client_details';
import {ClientDetailsModule} from './module';



initTestEnvironment();

describe('Client Details Component', () => {
  let facade: ClientDetailsFacade;
  let configFacade: ConfigFacadeMock;
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
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientDetailsModule,
          ],
          providers: [
            {provide: ConfigFacade, useFactory: () => configFacade},
            {provide: Router, useValue: {}},
          ],

        })
        .compileComponents();

    facade = TestBed.inject(ClientDetailsFacade);
  }));

  it('selects the first option in the timeline by default', () => {
    const subject = new Subject<ReadonlyArray<ClientVersion>>();
    Object.defineProperty(
        facade, 'selectedClientVersions$', {get: () => subject});

    const fixture = TestBed.createComponent(ClientDetails);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.
    subject.next(getClientVersions(clientVersionsMock));
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
       const subject = new Subject<ReadonlyArray<ClientVersion>>();
       Object.defineProperty(
           facade, 'selectedClientVersions$', {get: () => subject});
       const subjectClient = new Subject<Client>();
       Object.defineProperty(
           facade, 'selectedClient$', {get: () => subjectClient});

       const fixture = TestBed.createComponent(ClientDetails);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       subject.next(getClientVersions(clientVersionsMock));
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
