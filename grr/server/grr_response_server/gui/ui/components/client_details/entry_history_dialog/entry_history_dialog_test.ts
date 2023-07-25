import {OverlayContainer} from '@angular/cdk/overlay';
import {ComponentFixture, inject, TestBed, waitForAsync} from '@angular/core/testing';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {Client} from '../../../lib/models/client';
import {newClient} from '../../../lib/models/model_test_util';
import {initTestEnvironment} from '../../../testing';

import {EntryHistoryDialog, EntryHistoryDialogParams} from './entry_history_dialog';
import {EntryHistoryDialogModule} from './module';


initTestEnvironment();

describe('Entry History Dialog', () => {
  let fixture: ComponentFixture<EntryHistoryDialog>;
  let component: EntryHistoryDialog;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;
  let clientVersions: Client[];
  let providedData: EntryHistoryDialogParams;

  beforeEach(waitForAsync(() => {
    clientVersions = [
      newClient({
        osInfo: {
          architecture: 'x64',
          installDate: new Date(2019, 3, 11),
        },
        memorySize: BigInt(123),
        age: new Date(2020, 3, 11),
      }),
      newClient({
        osInfo: {
          architecture: 'x86',
          installDate: new Date(2010, 1, 1),
        },
        memorySize: BigInt(100),
        age: new Date(2000, 2, 1),
      }),
    ];
    TestBed
        .configureTestingModule({
          declarations: [EntryHistoryDialog],
          imports: [
            EntryHistoryDialogModule,
            NoopAnimationsModule,
            MatDialogModule,
          ],
          providers: [
            {provide: MAT_DIALOG_DATA, useFactory: () => providedData},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
    inject([OverlayContainer], (oc: OverlayContainer) => {
      overlayContainer = oc;
      overlayContainerElement = oc.getContainerElement();
    })();
  }));

  afterEach(() => {
    overlayContainer.ngOnDestroy();
  });

  it('is created successfully', () => {
    providedData = {
      path: ['osInfo', 'architecture'],
      type: 'primitive',
      clientVersions,
    };
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('extracts client property from the path provided into tableRows', () => {
    providedData = {
      path: ['osInfo', 'architecture'],
      type: 'primitive',
      clientVersions,
    };

    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const expectedTableRows = [
      {time: new Date(2020, 3, 11), version: 'x64'},
      {time: new Date(2000, 2, 1), version: 'x86'},
    ];

    expect(component.tableRows).toEqual(expectedTableRows);
  });

  it('extracts client property from the path provided into tableRows', () => {
    providedData = {
      path: ['memorySize'],
      type: 'primitive',
      clientVersions,
    };
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const expectedTableRows = [
      {time: new Date(2020, 3, 11), version: BigInt(123)},
      {time: new Date(2000, 2, 1), version: BigInt(100)},
    ];

    expect(component.tableRows).toEqual(expectedTableRows);
  });

  it('throws error on empty path', () => {
    providedData = {
      path: [],
      type: 'primitive',
      clientVersions,
    };

    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('throws error for paths to non-existent properties', () => {
    providedData = {
      path: ['osInfo', 'asdf', 'memorySize'],
      type: 'primitive',
      clientVersions,
    };

    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('throws error for paths with empty tokens', () => {
    providedData = {
      path: ['osInfo', ''],
      type: 'primitive',
      clientVersions,
    };

    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('shows a HumanReadableSize component for type \'size\'', () => {
    providedData = {
      path: ['memorySize'],
      type: 'size',
      clientVersions,
    };
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const sizeComponent =
        fixture.debugElement.query(By.css('human-readable-size'));
    expect(sizeComponent).toBeTruthy();
  });

  it('shows a Timestamp component for type \'timestamp\'', () => {
    providedData = {
      path: ['osInfo', 'installDate'],
      type: 'timestamp',
      clientVersions,
    };
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const timestampComponent =
        fixture.debugElement.query(By.css('app-timestamp'));
    expect(timestampComponent).toBeTruthy();
  });

  it('shows a users-details component for type \'user-list\'', () => {
    providedData = {
      path: ['users'],
      type: 'user-list',
      clientVersions,
    };
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const usersDetailsComponent =
        fixture.debugElement.query(By.css('users-details'));
    expect(usersDetailsComponent).toBeTruthy();
  });

  it('shows a interfaces-details component for type \'interface-list\'', () => {
    providedData = {
      path: ['networkInterfaces'],
      type: 'interface-list',
      clientVersions,
    };
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const interfacesDetailsComponent =
        fixture.debugElement.query(By.css('interfaces-details'));
    expect(interfacesDetailsComponent).toBeTruthy();
  });

  it('shows a volumes-details component for type \'volume-list\'', () => {
    providedData = {
      path: ['volumes'],
      type: 'volume-list',
      clientVersions,
    };

    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const volumesDetailsComponent =
        fixture.debugElement.query(By.css('volumes-details'));
    expect(volumesDetailsComponent).toBeTruthy();
  });
});
