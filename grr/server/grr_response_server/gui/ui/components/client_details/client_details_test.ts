import {async, discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {ApiModule} from '@app/lib/api/module';
import {Client} from '@app/lib/models/client';
import {newClient} from '@app/lib/models/model_test_util';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {ConfigFacade} from '@app/store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '@app/store/config_facade_test_util';
import {Subject} from 'rxjs';

import {initTestEnvironment} from '../../testing';

import {ClientDetails} from './client_details';
import {getClientVersions} from './client_diff';
import {ClientDetailsModule} from './module';

initTestEnvironment();

describe('Client Details Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let facade: ClientPageFacade;
  let configFacade: ConfigFacadeMock;
  const clientVersionsMock = [
    newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown-first',
      },
      age: new Date(2020, 1, 1),
    }),
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
  ];

  beforeEach(async(() => {
    paramsSubject = new Subject();
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientDetailsModule,
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {
                paramMap: paramsSubject,
              },
            },
            {provide: ConfigFacade, useFactory: () => configFacade},
            {provide: Router, useValue: {}},
          ],

        })
        .compileComponents();

    facade = TestBed.inject(ClientPageFacade);
  }));

  it('loads client information on route change', () => {
    const fixture = TestBed.createComponent(ClientDetails);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    const searchClientsSpy = spyOn(facade, 'selectClient');
    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    fixture.detectChanges();

    expect(searchClientsSpy).toHaveBeenCalledWith('C.1234');
  });

  it('selects the first option in the timeline by default', () => {
    // Prevent warnings from 404-ing API requests.
    spyOn(facade, 'selectClient');

    const subject = new Subject<Client[]>();
    Object.defineProperty(
        facade, 'selectedClientVersions$', {get: () => subject});

    const fixture = TestBed.createComponent(ClientDetails);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    subject.next(clientVersionsMock);
    fixture.detectChanges();
    const firstOption =
        fixture.debugElement.queryAll(By.css('mat-list-option'))[0];

    expect(firstOption.componentInstance.selected).toBe(true);
  });

  it('getClientVersions() correctly translates snapshots into client changes',
     () => {
       const snapshots = [
         // Client created
         newClient({
           clientId: 'C.1234',
           age: new Date(2020, 1, 1),
         }),
         // 3 User entries added
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'newUser1'},
             {username: 'newUser2'},
             {username: 'newUser3'},
           ],
           age: new Date(2020, 1, 2),
         }),
         // Oner User full name updated, One User home directory updated
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'newUser1', fullName: 'new User1 fullname'},
             {username: 'newUser2', homedir: 'homedir2'},
             {username: 'newUser3', fullName: 'new User3 fullname'},
           ],
           age: new Date(2020, 1, 3),
         }),
         // One User added, One User home directory updated
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'newUser1', fullName: 'new User1 fullname'},
             {username: 'newUser2', homedir: 'homedir2-change'},
             {username: 'newUser3', fullName: 'new User3 fullname'},
             {username: 'newUser4', fullName: 'new User4 fullname'},
           ],
           age: new Date(2020, 1, 4),
         }),
         // 4 User entries deleted
         newClient({
           clientId: 'C.1234',
           users: [],
           age: new Date(2020, 1, 5),
         }),
         // No changes besides non-relevant properties (e.g. age)
         newClient({
           clientId: 'C.1234',
           users: [],
           age: new Date(2020, 1, 6),
         }),
         // One Network interface added
         newClient({
           clientId: 'C.1234',
           users: [],
           networkInterfaces: [
             {
               interfaceName: 'lo',
               macAddress: '',
               addresses: [
                 {
                   addressType: 'IPv4',
                   ipAddress: '1.2.3.4',
                 },
               ],
             },
           ],
           age: new Date(2020, 1, 7),
         }),
         // One IP address added, One IP address updated
         newClient({
           clientId: 'C.1234',
           users: [],
           networkInterfaces: [
             {
               interfaceName: 'lo',
               macAddress: '',
               addresses: [
                 {
                   addressType: 'IPv4',
                   ipAddress: '1.2.3.40',
                 },
                 {
                   addressType: 'IPv4',
                   ipAddress: '127.0.0.1',
                 },
               ],
             },
           ],
           age: new Date(2020, 1, 7),
         }),
         // More than 3 changes => X new changes
         newClient({
           clientId: 'C.1234',
           users: [
             {username: 'foo'},
           ],
           memorySize: BigInt(123),
           agentInfo: {
             clientName: 'GRR',
           },
           osInfo: {
             system: 'linux',
           },
           age: new Date(2020, 1, 8),
         }),
       ];

       const expectedClientChanges = [
         {
           client: snapshots[0],
           changes: ['Client created'],
         },
         {
           client: snapshots[1],
           changes: ['3 User entries added'],
         },
         {
           client: snapshots[2],
           changes: [
             '2 User full name entries added', 'One User home directory added'
           ],
         },
         {
           client: snapshots[3],
           changes: ['One User home directory updated', 'One User added'],
         },
         {
           client: snapshots[4],
           changes: ['4 User entries deleted'],
         },
         // Next snapshot is identical to the one before, so it is skipped
         {
           client: snapshots[6],
           changes: ['One Network interface added'],
         },
         {
           client: snapshots[7],
           changes: ['One Network address added', 'One IP address updated'],
         },
         {
           client: snapshots[8],
           changes: ['5 new changes'],
         },
       ].reverse();

       const clientChanges = getClientVersions(snapshots.reverse());

       expect(clientChanges.map(
                  change => {change.client, [...change.changes].sort()}))
           .toEqual(expectedClientChanges.map(expectedChange => {
             expectedChange.client,
             expectedChange.changes.sort()
           }));
     });

  it('getClientVersions() reduces sequences of identical snapshots to the oldest snapshot',
     () => {
       const snapshots = [
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: true,
           age: new Date(2020, 2, 2),
         }),
         newClient({
           clientId: 'C.1234',
           fleetspeakEnabled: true,
           age: new Date(2020, 1, 1),
         })
       ];

       const expectedClientChanges = [
         {
           client: snapshots[1],
           changes: ['Client created'],
         },
       ];

       const clientChanges = getClientVersions(snapshots);
       expect(clientChanges).toEqual(expectedClientChanges);
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
       // Prevent warnings from 404-ing API requests.
       spyOn(facade, 'selectClient');

       const subject = new Subject<Client[]>();
       Object.defineProperty(
           facade, 'selectedClientVersions$', {get: () => subject});
       const subjectClient = new Subject<Client>();
       Object.defineProperty(
           facade, 'selectedClient$', {get: () => subjectClient});

       const fixture = TestBed.createComponent(ClientDetails);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
       subject.next(clientVersionsMock);
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
