import {OverlayContainer} from '@angular/cdk/overlay';
import {async, ComponentFixture, inject, TestBed} from '@angular/core/testing';
import {MAT_DIALOG_DATA, MatDialogModule} from '@angular/material/dialog';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
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

    providedData.path = 'memorySize';
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expectedTableRows = [
      {time: new Date(2020, 3, 11), version: BigInt(123) as any},
      {time: new Date(2000, 2, 1), version: BigInt(100) as any},
    ];

    expect(component.tableRows).toEqual(expectedTableRows);

    providedData.path = '';  // Empty path string => Error
    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();

    providedData.path =
        'osInfo.asdf.memorySize';  // Non-existant property => Error
    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();

    providedData.path = 'osInfo.';  // Trailing dot => Error
    expect(() => TestBed.createComponent(EntryHistoryDialog)).toThrowError();
  });

  it('shows a HumanReadableSize component for type \'size\'', () => {
    providedData.type = 'size';
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const sizeComponent =
        fixture.debugElement.query(By.css('human-readable-size'));
    expect(sizeComponent).toBeTruthy();
  });

  it('shows a Timestamp component for type \'timestamp\'', () => {
    providedData.type = 'timestamp';
    providedData.path = 'osInfo.installDate'
    fixture = TestBed.createComponent(EntryHistoryDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
    const timestampComponent = fixture.debugElement.query(By.css('timestamp'));
    expect(timestampComponent).toBeTruthy();
  });
});
