import {OverlayContainer} from '@angular/cdk/overlay';
import {async, ComponentFixture, inject, TestBed} from '@angular/core/testing';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Client} from '@app/lib/models/client';
import {newClient} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {EntryHistoryDialog, EntryHistoryDialogParams} from './entry_history_dialog';
import {EntryHistoryDialogModule} from './module';

initTestEnvironment();

describe('Entry History Dialog', () => {
  let fixture: ComponentFixture<EntryHistoryDialog>;
  let component: EntryHistoryDialog;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;
  let clientVersions: Client[];

  beforeEach(async(() => {
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
  }));

  afterEach(() => {
    overlayContainer.ngOnDestroy();
  });

  function configureTestingModule(providedData: EntryHistoryDialogParams) {
    TestBed
        .configureTestingModule({
          declarations: [EntryHistoryDialog],
          imports: [
            EntryHistoryDialogModule,
            NoopAnimationsModule,  // This makes test faster and more stable.
            MatDialogModule,
          ],
          providers: [
            {provide: MAT_DIALOG_DATA, useValue: providedData},
          ],
        })
        .compileComponents();
    inject([OverlayContainer], (oc: OverlayContainer) => {
      overlayContainer = oc;
      overlayContainerElement = oc.getContainerElement();
    })();
  }

  it('is created successfully', () => {
    configureTestingModule({
      path: 'osInfo.architecture',
      type: 'primitive',
      clientVersions,
    });
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('extracts client property from the path provided into tableRows', () => {
    configureTestingModule({
      path: 'osInfo.architecture',
      type: 'primitive',
      clientVersions,
    });

    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const expectedTableRows = [
      {time: new Date(2020, 3, 11), version: 'x64' as any},
      {time: new Date(2000, 2, 1), version: 'x86' as any},
    ];

    expect(component.tableRows).toEqual(expectedTableRows);
  });

  it('extracts client property from the path provided into tableRows', () => {
    configureTestingModule({
      path: 'memorySize',
      type: 'primitive',
      clientVersions,
    });
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();

    const expectedTableRows = [
      {time: new Date(2020, 3, 11), version: BigInt(123) as any},
      {time: new Date(2000, 2, 1), version: BigInt(100) as any},
    ];

    expect(component.tableRows).toEqual(expectedTableRows);
  });

  it('throws error on path empty string', () => {
    configureTestingModule({
      path: '',
      type: 'primitive',
      clientVersions,
    });

    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('throws error for paths to non-existant properties', () => {
    configureTestingModule({
      path: 'osInfo.asdf.memorySize',
      type: 'primitive',
      clientVersions,
    });

    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('throws error for paths with trailing dot', () => {
    configureTestingModule({
      path: 'osInfo.',
      type: 'primitive',
      clientVersions,
    });

    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('shows a HumanReadableSize component for type \'size\'', () => {
    configureTestingModule({
      path: 'memorySize',
      type: 'size',
      clientVersions,
    });
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const sizeComponent =
        fixture.debugElement.query(By.css('human-readable-size'));
    expect(sizeComponent).toBeTruthy();
  });

  it('shows a Timestamp component for type \'timestamp\'', () => {
    configureTestingModule({
      path: 'osInfo.installDate',
      type: 'timestamp',
      clientVersions,
    });
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const timestampComponent = fixture.debugElement.query(By.css('timestamp'));
    expect(timestampComponent).toBeTruthy();
  });

  it('shows a users-details component for type \'user-list\'', () => {
    configureTestingModule({
      path: 'users',
      type: 'user-list',
      clientVersions,
    });
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const usersDetailsComponent =
        fixture.debugElement.query(By.css('users-details'));
    expect(usersDetailsComponent).toBeTruthy();
  });

  it('shows a interfaces-details component for type \'interface-list\'', () => {
    configureTestingModule({
      path: 'networkInterfaces',
      type: 'interface-list',
      clientVersions,
    });
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const interfacesDetailsComponent =
        fixture.debugElement.query(By.css('interfaces-details'));
    expect(interfacesDetailsComponent).toBeTruthy();
  });

  it('shows a volumes-details component for type \'volume-list\'', () => {
    configureTestingModule({
      path: 'volumes',
      type: 'volume-list',
      clientVersions,
    });

    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const volumesDetailsComponent =
        fixture.debugElement.query(By.css('volumes-details'));
    expect(volumesDetailsComponent).toBeTruthy();
  });
});
