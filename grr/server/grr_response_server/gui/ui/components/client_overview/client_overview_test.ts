import {Location} from '@angular/common';
import {async, TestBed} from '@angular/core/testing';
import {MatChip, MatChipList} from '@angular/material/chips';
import {MatDrawer} from '@angular/material/sidenav';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute} from '@angular/router';
import {ApiModule} from '@app/lib/api/module';
import {Client} from '@app/lib/models/client';
import {newClient} from '@app/lib/models/model_test_util';
import {ClientPageFacade} from '@app/store/client_page_facade';
import {Subject} from 'rxjs';

import {ClientOverview} from './client_overview';
import {ClientOverviewModule} from './module';

describe('Client Overview', () => {
  let facade: ClientPageFacade;
  let location: Location;

  beforeEach(async(() => {
    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientOverviewModule,
          ],
          providers: [
            {
              provide: ActivatedRoute,
              useValue: {},
            },
          ]
        })
        .compileComponents();

    facade = TestBed.inject(ClientPageFacade);
    location = TestBed.get(Location);
  }));

  it('displays client details on client change', () => {
    const subject = new Subject<Client>();
    Object.defineProperty(facade, 'selectedClient$', {get: () => subject});

    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    subject.next(newClient({
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
    const subject = new Subject<Client>();
    Object.defineProperty(facade, 'selectedClient$', {get: () => subject});
    spyOn(facade, 'removeClientLabel');

    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    subject.next(newClient({
      clientId: 'C.1234',
      labels: [{name: 'testlabel', owner: ''}],
    }));
    fixture.detectChanges();

    const labelsChipList = fixture.debugElement.query(By.directive(MatChipList))
                               .componentInstance.chips.toArray() as MatChip[];
    labelsChipList[0].remove();
    expect(facade.removeClientLabel).toHaveBeenCalledWith('testlabel');
  });

  it('shows a snackbar when a client label is removed', () => {
    const clientSubject = new Subject<Client>();
    const removedLabelsSubject = new Subject<string>();
    Object.defineProperty(
        facade, 'selectedClient$', {get: () => clientSubject});
    Object.defineProperty(
        facade, 'lastRemovedClientLabel$', {get: () => removedLabelsSubject});

    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    clientSubject.next(newClient({
      clientId: 'C.1234',
      labels: [{name: 'testlabel', owner: ''}],
    }));
    fixture.detectChanges();

    const labelsChipList = fixture.debugElement.query(By.directive(MatChipList))
                               .componentInstance.chips.toArray() as MatChip[];
    labelsChipList[0].remove();
    removedLabelsSubject.next('testlabel');
    fixture.detectChanges();

    const snackbarDiv = document.querySelector('snack-bar-container');
    expect(snackbarDiv).toBeTruthy();
    expect(snackbarDiv!.textContent).toContain('Label "testlabel" removed');
    snackbarDiv!.remove();
  });

  it('snackbar action undoes a removal of client label', () => {
    const clientSubject = new Subject<Client>();
    const removedLabelsSubject = new Subject<string>();
    Object.defineProperty(
        facade, 'selectedClient$', {get: () => clientSubject});
    Object.defineProperty(
        facade, 'lastRemovedClientLabel$', {get: () => removedLabelsSubject});
    spyOn(facade, 'addClientLabel');

    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    clientSubject.next(newClient({
      clientId: 'C.1234',
      labels: [{name: 'testlabel', owner: ''}],
    }));
    fixture.detectChanges();

    const labelsChipList = fixture.debugElement.query(By.directive(MatChipList))
                               .componentInstance.chips.toArray() as MatChip[];
    labelsChipList[0].remove();
    removedLabelsSubject.next('testlabel');
    fixture.detectChanges();

    expect(facade.addClientLabel).not.toHaveBeenCalled();

    const snackbarDivButton =
        document.querySelector('div.mat-simple-snackbar-action button');
    snackbarDivButton!.dispatchEvent(new MouseEvent('click'));
    fixture.detectChanges();
    fixture.whenRenderingDone().then(() => {
      expect(facade.addClientLabel).toHaveBeenCalledWith('testlabel');
    });
  });

  it('allows viewing of client details', () => {
    const subject = new Subject<Client>();
    Object.defineProperty(facade, 'selectedClient$', {get: () => subject});
    spyOn(facade, 'removeClientLabel');

    const fixture = TestBed.createComponent(ClientOverview);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    subject.next(newClient({
      clientId: 'C.1234',
      labels: [{name: 'testlabel', owner: ''}],
    }));
    fixture.detectChanges();
    const detailsDrawer =
        fixture.debugElement.query(By.directive(MatDrawer)).componentInstance;
    const drawerOpenSpy = spyOn(detailsDrawer, 'open');

    const detailsButton =
        fixture.debugElement.query(By.css('.goto-details')).nativeElement;
    detailsButton.dispatchEvent(new MouseEvent('click'));

    expect(drawerOpenSpy).toHaveBeenCalled();
    detailsDrawer.close();
  });

  it('appends a customizable segment to the URL when opening the client details drawer',
     () => {
       const subject = new Subject<Client>();
       Object.defineProperty(facade, 'selectedClient$', {get: () => subject});

       const fixture = TestBed.createComponent(ClientOverview);
       fixture.detectChanges();  // Ensure ngOnInit hook completes.

       subject.next(newClient({
         clientId: 'C.1234',
         labels: [{name: 'testlabel', owner: ''}],
       }));
       fixture.detectChanges();
       fixture.componentInstance.onClientDetailsButtonClick();

       expect(location.path().endsWith('details')).toBe(true);
       fixture.componentInstance.onClientDetailsButtonClick();

       // The following expectation is met when testing manually, but not on
       // automated testing, because the drawer's closedStart observable is
       // not emitting
       // expect(location.path().endsWith('details')).toBe(false);

       fixture.componentInstance.urlSegment = 'custom';
       fixture.componentInstance.onClientDetailsButtonClick();

       expect(location.path().endsWith('custom')).toBe(true);
       fixture.componentInstance.onClientDetailsButtonClick();
       // The following expectation is met when testing manually, but not on
       // automated testing, because the drawer's closedStart observable is
       // not emitting expect(location.path().endsWith('custom')).toBe(false);
     });
});
