import {QueryList} from '@angular/core';
import {async, discardPeriodicTasks, fakeAsync, TestBed, tick} from '@angular/core/testing';
import {MatChip, MatChipList} from '@angular/material/chips';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, Router} from '@angular/router';
import {ApiModule} from '@app/lib/api/module';
import {newClient} from '@app/lib/models/model_test_util';
import {Subject} from 'rxjs';

import {Client} from '../../lib/models/client';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';
import {ConfigFacadeMock, mockConfigFacade} from '../../store/config_facade_test_util';
import {initTestEnvironment} from '../../testing';

import {Client as ClientComponent} from './client';
import {ClientModule} from './module';



initTestEnvironment();

describe('Client Component', () => {
  let paramsSubject: Subject<Map<string, string>>;
  let facade: ClientPageFacade;
  let configFacade: ConfigFacadeMock;

  beforeEach(async(() => {
    paramsSubject = new Subject();
    configFacade = mockConfigFacade();

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            ClientModule,
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
    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    const searchClientsSpy = spyOn(facade, 'selectClient');
    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    fixture.detectChanges();

    expect(searchClientsSpy).toHaveBeenCalledWith('C.1234');
  });

  it('displays client details on client change', () => {
    // Prevent warnings from 404-ing API requests.
    spyOn(facade, 'selectClient');

    const subject = new Subject<Client>();
    Object.defineProperty(facade, 'selectedClient$', {get: () => subject});

    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    subject.next(newClient({
      clientId: 'C.1234',
      knowledgeBase: {
        fqdn: 'foo.unknown',
      },
      lastSeenAt: new Date(1571789996678),
    }));
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('C.1234');
    expect(text).toContain('foo.unknown');
  });

  it('allows removal of client labels', () => {
    // Prevent warnings from 404-ing API requests.
    spyOn(facade, 'selectClient');

    const subject = new Subject<Client>();
    Object.defineProperty(facade, 'selectedClient$', {get: () => subject});
    spyOn(facade, 'removeClientLabel');

    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
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
    // Prevent warnings from 404-ing API requests.
    spyOn(facade, 'selectClient');

    const clientSubject = new Subject<Client>();
    const removedLabelsSubject = new Subject<string>();
    Object.defineProperty(
        facade, 'selectedClient$', {get: () => clientSubject});
    Object.defineProperty(
        facade, 'lastRemovedClientLabel$', {get: () => removedLabelsSubject});

    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
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

  it('doesn\'t show a snackbar when a client label request errors', () => {
    // Prevent warnings from 404-ing API requests.
    spyOn(facade, 'selectClient');

    const clientSubject = new Subject<Client>();
    const removedLabelsSubject = new Subject<string>();
    Object.defineProperty(
        facade, 'selectedClient$', {get: () => clientSubject});
    Object.defineProperty(
        facade, 'lastRemovedClientLabel$', {get: () => removedLabelsSubject});

    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
    clientSubject.next(newClient({
      clientId: 'C.1234',
      labels: [{name: 'testlabel', owner: ''}],
    }));
    fixture.detectChanges();

    const labelsChipList = fixture.debugElement.query(By.directive(MatChipList))
                               .componentInstance.chips.toArray() as MatChip[];
    labelsChipList[0].remove();
    removedLabelsSubject.error(new Error('Some error'));
    fixture.detectChanges();

    const snackbarDiv = document.querySelector('snack-bar-container');
    expect(snackbarDiv).not.toBeTruthy();
  });

  it('snackbar action undoes a removal of client label', () => {
    // Prevent warnings from 404-ing API requests.
    spyOn(facade, 'selectClient');

    const clientSubject = new Subject<Client>();
    const removedLabelsSubject = new Subject<string>();
    Object.defineProperty(
        facade, 'selectedClient$', {get: () => clientSubject});
    Object.defineProperty(
        facade, 'lastRemovedClientLabel$', {get: () => removedLabelsSubject});
    spyOn(facade, 'addClientLabel');

    const fixture = TestBed.createComponent(ClientComponent);
    fixture.detectChanges();  // Ensure ngOnInit hook completes.

    paramsSubject.next(new Map(Object.entries({id: 'C.1234'})));
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
});
