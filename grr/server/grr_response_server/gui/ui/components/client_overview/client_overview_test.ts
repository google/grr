import {discardPeriodicTasks, fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatChip, MatChipList} from '@angular/material/chips';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ApiModule} from '../../lib/api/module';
import {newClient} from '../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';

import {ClientOverview} from './client_overview';
import {ClientOverviewModule} from './module';



describe('Client Overview', () => {
  let store: ClientPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    store = mockClientPageGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientOverviewModule,
          ],
          providers: [{
            provide: ClientPageGlobalStore,
            useFactory: () => store,
          }],

        })
        .compileComponents();
  }));

  it('displays client details on client change', () => {
    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    store.mockedObservables.selectedClient$.next(newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown',
      },
    }));
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1234');
    expect(text).toContain('foo.unknown');
  });

  it('allows removal of client labels', () => {
    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    store.mockedObservables.selectedClient$.next(newClient({
      clientId: 'C.1234',
      labels: [{name: 'testlabel', owner: ''}],
    }));
    fixture.detectChanges();

    const labelsChipList = fixture.debugElement.query(By.directive(MatChipList))
                               .componentInstance.chips.toArray() as MatChip[];
    labelsChipList[0].remove();
    expect(store.removeClientLabel).toHaveBeenCalledWith('testlabel');
  });

  it('shows a snackbar when a client label is removed', () => {
    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    store.mockedObservables.selectedClient$.next(newClient({
      clientId: 'C.1234',
      labels: [{name: 'testlabel', owner: ''}],
    }));
    fixture.detectChanges();

    const labelsChipList = fixture.debugElement.query(By.directive(MatChipList))
                               .componentInstance.chips.toArray() as MatChip[];
    labelsChipList[0].remove();
    store.mockedObservables.lastRemovedClientLabel$.next('testlabel');
    fixture.detectChanges();

    const snackbarDiv = document.querySelector('snack-bar-container');
    expect(snackbarDiv).toBeTruthy();
    expect(snackbarDiv!.textContent).toContain('Label "testlabel" removed');
    snackbarDiv!.remove();
  });

  it('snackbar action undoes a removal of client label', fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientOverview);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       store.mockedObservables.selectedClient$.next(newClient({
         clientId: 'C.1234',
         labels: [{name: 'testlabel', owner: ''}],
       }));
       fixture.detectChanges();

       const labelsChipList =
           fixture.debugElement.query(By.directive(MatChipList))
               .componentInstance.chips.toArray() as MatChip[];
       labelsChipList[0].remove();
       store.mockedObservables.lastRemovedClientLabel$.next('testlabel');
       fixture.detectChanges();

       expect(store.addClientLabel).not.toHaveBeenCalled();

       const snackbarDivButton =
           document.querySelector('div.mat-simple-snackbar-action button');
       snackbarDivButton!.dispatchEvent(new MouseEvent('click'));
       fixture.detectChanges();
       tick();
       discardPeriodicTasks();
       expect(store.addClientLabel).toHaveBeenCalledWith('testlabel');
     }));
});
