import {Component, Input} from '@angular/core';
import {discardPeriodicTasks, fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {MatChipList} from '@angular/material/chips';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterTestingModule} from '@angular/router/testing';

import {ApiModule} from '../../lib/api/module';
import {newClient, newClientApproval, newFlowDescriptor} from '../../lib/models/model_test_util';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ClientPageGlobalStoreMock, mockClientPageGlobalStore} from '../../store/client_page_global_store_test_util';
import {STORE_PROVIDERS} from '../../store/store_test_providers';
import {ApprovalChip} from '../client/approval_chip/approval_chip';

import {ClientOverview} from './client_overview';
import {ClientOverviewModule} from './module';


@Component({
  template: `<client-overview [collapsed]="collapsed"></client-overview>`,
})
class TestHostComponent {
  @Input() collapsed: boolean = false;
}

describe('Client Overview', () => {
  let store: ClientPageGlobalStoreMock;

  beforeEach(waitForAsync(() => {
    store = mockClientPageGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            RouterTestingModule,
            ClientOverviewModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [
            ...STORE_PROVIDERS,
            {
              provide: ClientPageGlobalStore,
              useFactory: () => store,
            },
          ],
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

    const labelsChipListEl = fixture.debugElement.query(By.css('.labels'))
                                 .query(By.directive(MatChipList))
                                 .componentInstance as MatChipList;
    expect(labelsChipListEl).not.toBeNull();
    const labelsChipList = labelsChipListEl.chips.toArray();
    expect(labelsChipList.length).toBe(1);
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

    const labelsChipListEl = fixture.debugElement.query(By.css('.labels'))
                                 .query(By.directive(MatChipList))
                                 .componentInstance as MatChipList;
    expect(labelsChipListEl).not.toBeNull();
    const labelsChipList = labelsChipListEl.chips.toArray();
    expect(labelsChipList.length).toBe(1);
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

       const labelsChipListEl = fixture.debugElement.query(By.css('.labels'))
                                    .query(By.directive(MatChipList))
                                    .componentInstance as MatChipList;
       expect(labelsChipListEl).not.toBeNull();
       const labelsChipList = labelsChipListEl.chips.toArray();
       expect(labelsChipList.length).toBe(1);
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

  it('shows approval information', () => {
    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();

    store.mockedObservables.selectedClient$.next(newClient());
    store.mockedObservables.approvalsEnabled$.next(true);
    store.mockedObservables.latestApproval$.next(newClientApproval(
        {status: {type: 'pending', reason: 'Need 1 more approver'}}));
    fixture.detectChanges();

    const approvalChip = fixture.debugElement.query(By.directive(ApprovalChip));
    expect(approvalChip).not.toBeNull();
    expect(approvalChip.componentInstance.approval)
        .toEqual(jasmine.objectContaining(
            {status: {type: 'pending', reason: 'Need 1 more approver'}}));
  });

  it('hides approval info if approvals are disabled', () => {
    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();

    store.mockedObservables.selectedClient$.next(newClient());
    store.mockedObservables.approvalsEnabled$.next(false);
    fixture.detectChanges();

    const approvalChip = fixture.debugElement.query(By.directive(ApprovalChip));
    expect(approvalChip).toBeNull();
  });

  it('collapses if [collapsed] input is set to true', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    store.mockedObservables.selectedClient$.next(newClient());
    store.mockedObservables.approvalsEnabled$.next(false);
    fixture.detectChanges();

    const initialHeight = fixture.nativeElement.offsetHeight;
    expect(initialHeight).toBeGreaterThan(0);

    fixture.componentInstance.collapsed = true;
    fixture.detectChanges();

    expect(fixture.nativeElement.offsetHeight).toBeLessThan(initialHeight);
  });

  it('shows a warning for legacy comms clients', () => {
    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    store.mockedObservables.selectedClient$.next(newClient({
      clientId: 'C.1234',
      fleetspeakEnabled: false,
    }));
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .toContain('Outdated');
  });

  it('shows no warning for Fleetspeak clients', () => {
    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    store.mockedObservables.selectedClient$.next(newClient({
      clientId: 'C.1234',
      fleetspeakEnabled: true,
    }));
    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent)
        .not.toContain('Outdated');
  });

  it('shows a button to trigger online notification', fakeAsync(() => {
       const fixture = TestBed.createComponent(ClientOverview);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       store.mockedObservables.selectedClient$.next(newClient({
         clientId: 'C.1234',
         fleetspeakEnabled: false,
         lastSeenAt: new Date(2000, 1, 1),
       }));
       store.mockedObservables.hasAccess$.next(true);
       fixture.detectChanges();

       const button = fixture.debugElement.query(
           By.css('button[name=online-notification]'));
       button.triggerEventHandler('click', null);

       expect(store.startFlowConfiguration)
           .toHaveBeenCalledOnceWith('OnlineNotification');

       store.mockedObservables.selectedFlowDescriptor$.next(newFlowDescriptor({
         name: 'OnlineNotification',
         defaultArgs: {email: 'foo@example.com'}
       }));

       tick();

       expect(store.startFlow).toHaveBeenCalledOnceWith({
         email: 'foo@example.com'
       });

       discardPeriodicTasks();
     }));
});
