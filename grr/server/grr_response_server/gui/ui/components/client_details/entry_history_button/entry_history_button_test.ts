import {async, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Subject} from 'rxjs';

import {ApiModule} from '../../../lib/api/module';
import {Client} from '../../../lib/models/client';
import {newClient} from '../../../lib/models/model_test_util';
import {getClientEntriesChanged} from '../../../store/client_details_diff';
import {ClientDetailsFacade} from '../../../store/client_details_facade';
import {initTestEnvironment} from '../../../testing';

import {EntryHistoryButton} from './entry_history_button';
import {EntryHistoryButtonModule} from './module';



initTestEnvironment();

describe('Entry History Button Component', () => {
  let facade: ClientDetailsFacade;
  const clientVersionsMock = [
    newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown-first',
      },
      memorySize: BigInt(123),
      age: new Date(2020, 2, 1),
    }),
    newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown-first',
      },
      memorySize: BigInt(12),
      age: new Date(2020, 1, 1),
    }),
    newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown-changed',
      },
      memorySize: BigInt(1),
      users: [
        {username: 'foo'},
        {username: 'bar'},
        {username: 'hidden-username'},
      ],
      age: new Date(2019, 12, 1),
    }),
  ];

  // TODO(user): Change to waitForAsync once we run on Angular 10, which
  //  in turn requires TypeScript 3.9.
  // tslint:disable-next-line:deprecation
  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            EntryHistoryButtonModule,
          ],

        })
        .compileComponents();

    facade = TestBed.inject(ClientDetailsFacade);
  }));

  it('shows "1 change" button when there is one change', fakeAsync(() => {
       const subject = new Subject<Map<string, ReadonlyArray<Client>>>();
       Object.defineProperty(
           facade, 'selectedClientEntriesChanged$', {get: () => subject});

       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'knowledgeBase.fqdn';
       fixture.detectChanges();

       subject.next(getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeTruthy();
       expect(fixture.nativeElement.textContent).toEqual('1 change');
     }));

  it('shows "N changes" button when there is more than one change',
     fakeAsync(() => {
       const subject = new Subject<Map<string, ReadonlyArray<Client>>>();
       Object.defineProperty(
           facade, 'selectedClientEntriesChanged$', {get: () => subject});

       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'memorySize';
       fixture.detectChanges();

       subject.next(getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeTruthy();
       expect(fixture.nativeElement.textContent).toEqual('2 changes');
     }));

  it('doesn\'t show button when there is no change in a defined property',
     fakeAsync(() => {
       const subject = new Subject<Map<string, ReadonlyArray<Client>>>();
       Object.defineProperty(
           facade, 'selectedClientEntriesChanged$', {get: () => subject});

       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'clientId';
       fixture.detectChanges();

       subject.next(getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeFalsy();
     }));

  it('doesn\'t show button when the path points to an undefined property',
     fakeAsync(() => {
       const subject = new Subject<Map<string, ReadonlyArray<Client>>>();
       Object.defineProperty(
           facade, 'selectedClientEntriesChanged$', {get: () => subject});

       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'volumes.foo.bar';
       fixture.detectChanges();

       subject.next(getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeFalsy();
     }));
});
