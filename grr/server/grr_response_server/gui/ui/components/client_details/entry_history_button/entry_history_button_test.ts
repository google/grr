import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ApiModule} from '../../../lib/api/module';
import {newClient} from '../../../lib/models/model_test_util';
import {getClientEntriesChanged} from '../../../store/client_details_diff';
import {ClientDetailsGlobalStore} from '../../../store/client_details_global_store';
import {ClientDetailsGlobalStoreMock, mockClientDetailsGlobalStore} from '../../../store/client_details_global_store_test_util';
import {initTestEnvironment} from '../../../testing';

import {EntryHistoryButton} from './entry_history_button';
import {EntryHistoryButtonModule} from './module';


initTestEnvironment();

describe('Entry History Button Component', () => {
  let store: ClientDetailsGlobalStoreMock;
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

  beforeEach(waitForAsync(() => {
    store = mockClientDetailsGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            EntryHistoryButtonModule,
          ],
          providers: [
            {provide: ClientDetailsGlobalStore, useFactory: () => store},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('shows "1 change" button when there is one change', fakeAsync(() => {
       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'knowledgeBase.fqdn';
       fixture.detectChanges();

       store.mockedObservables.selectedClientEntriesChanged$.next(
           getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeTruthy();
       expect(fixture.nativeElement.textContent).toEqual('1 change');
     }));

  it('shows "N changes" button when there is more than one change',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'memorySize';
       fixture.detectChanges();

       store.mockedObservables.selectedClientEntriesChanged$.next(
           getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeTruthy();
       expect(fixture.nativeElement.textContent).toEqual('2 changes');
     }));

  it('doesn\'t show button when there is no change in a defined property',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'clientId';
       fixture.detectChanges();

       store.mockedObservables.selectedClientEntriesChanged$.next(
           getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeFalsy();
     }));

  it('doesn\'t show button when the path points to an undefined property',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(EntryHistoryButton);
       fixture.componentInstance.path = 'volumes.foo.bar';
       fixture.detectChanges();

       store.mockedObservables.selectedClientEntriesChanged$.next(
           getClientEntriesChanged(clientVersionsMock));
       tick();
       fixture.detectChanges();

       expect(fixture).toBeTruthy();
       expect(fixture.debugElement.query(By.css('button'))).toBeFalsy();
     }));
});
