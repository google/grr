import {OverlayContainer} from '@angular/cdk/overlay';
import {async, ComponentFixture, inject, TestBed} from '@angular/core/testing';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {Client} from '@app/lib/models/client';
import {newClient} from '@app/lib/models/model_test_util';
import {initTestEnvironment} from '@app/testing';

import {ClientDetailsModule} from '../module';

import {EntryHistoryDialog, EntryHistoryDialogParams} from './entry_history_dialog';

initTestEnvironment();

describe('Entry History Dialog', () => {
  let fixture: ComponentFixture<EntryHistoryDialog>;
  let component: EntryHistoryDialog;
  let providedData: EntryHistoryDialogParams;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;

  beforeEach(async(() => {
    providedData = {
      path: 'osInfo.architecture',
      type: 'primitive',
      clientVersions: [
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
      ],
    };

    TestBed
        .configureTestingModule({
          declarations: [EntryHistoryDialog],
          imports: [
            ClientDetailsModule,
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
  }));

  afterEach(() => {
    overlayContainer.ngOnDestroy();
  });

  it('is created successfully', () => {
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('extracts client property from the path provided into tableRows', () => {
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();

    let expectedTableRows = [
      {time: new Date(2020, 3, 11), version: 'x64' as any},
      {time: new Date(2000, 2, 1), version: 'x86' as any},
    ];

    expect(component.tableRows).toEqual(expectedTableRows);

    // @ts-ignore
    providedData.path = 'memorySize';
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expectedTableRows = [
      {time: new Date(2020, 3, 11), version: BigInt(123) as any},
      {time: new Date(2000, 2, 1), version: BigInt(100) as any},
    ];

    expect(component.tableRows).toEqual(expectedTableRows);

    // @ts-ignore
    providedData.path = '';  // Empty path string => Error
    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();

    // @ts-ignore
    providedData.path =
        'osInfo.asdf.memorySize';  // Non-existant property => Error
    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();

    // @ts-ignore
    providedData.path = 'osInfo.';  // Trailing dot => Error
    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('shows a HumanReadableSize component for type \'size\'', () => {
    // @ts-ignore
    providedData.type = 'size';
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const sizeComponent =
        fixture.debugElement.query(By.css('human-readable-size'));
    expect(sizeComponent).toBeTruthy();
  });

  it('shows a Timestamp component for type \'timestamp\'', () => {
    // @ts-ignore
    providedData.type = 'timestamp';
    // @ts-ignore
    providedData.path = 'osInfo.installDate'
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const timestampComponent = fixture.debugElement.query(By.css('timestamp'));
    expect(timestampComponent).toBeTruthy();
  });

  it('shows a users-details component for type \'user-list\'', () => {
    // @ts-ignore
    providedData.type = 'user-list';
    // @ts-ignore
    providedData.path = 'users'
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const usersDetailsComponent =
        fixture.debugElement.query(By.css('users-details'));
    expect(usersDetailsComponent).toBeTruthy();
  });

  it('shows a interfaces-details component for type \'interface-list\'', () => {
    // @ts-ignore
    providedData.type = 'interface-list';
    // @ts-ignore
    providedData.path = 'networkInterfaces'
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const interfacesDetailsComponent =
        fixture.debugElement.query(By.css('interfaces-details'));
    expect(interfacesDetailsComponent).toBeTruthy();
  });

  it('shows a volumes-details component for type \'volume-list\'', () => {
    // @ts-ignore
    providedData.type = 'volume-list';
    // @ts-ignore
    providedData.path = 'volumes'
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const volumesDetailsComponent =
        fixture.debugElement.query(By.css('volumes-details'));
    expect(volumesDetailsComponent).toBeTruthy();
  });
});
