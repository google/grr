import {OverlayContainer} from '@angular/cdk/overlay';
import {ComponentFixture, inject, TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MAT_DIALOG_DATA, MatDialogModule, MatDialogRef} from '@angular/material/dialog';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ClientLabel} from '../../lib/models/client';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../testing';

import {ClientAddLabelDialog} from './client_add_label_dialog';
import {ClientAddLabelDialogModule} from './module';

initTestEnvironment();

describe('Client Add Label Dialog', () => {
  let fixture: ComponentFixture<ClientAddLabelDialog>;
  let component: ClientAddLabelDialog;
  const clientLabels: ReadonlyArray<ClientLabel> =
      [{owner: '', name: 'label1'}, {owner: '', name: 'testlabel'}];

  let configGlobalStoreMock: ConfigGlobalStoreMock;
  const dialogRefMock = {close() {}};
  let dialogCloseSpy: jasmine.Spy;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;

  beforeEach(waitForAsync(() => {
    configGlobalStoreMock = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          declarations: [],
          imports: [
            ClientAddLabelDialogModule,
            NoopAnimationsModule,
            ReactiveFormsModule,
            MatDialogModule,
          ],
          providers: [
            {provide: MatDialogRef, useFactory: () => dialogRefMock},
            {provide: MAT_DIALOG_DATA, useFactory: () => clientLabels}, {
              provide: ConfigGlobalStore,
              useFactory: () => configGlobalStoreMock
            }
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

  beforeEach(() => {
    fixture = TestBed.createComponent(ClientAddLabelDialog);
    component = fixture.componentInstance;
    dialogCloseSpy = spyOn(dialogRefMock, 'close');
    configGlobalStoreMock.mockedObservables.clientsLabels$.next([
      'label1',
      'unusedlabel',
      'testlabel',
    ]);
    fixture.detectChanges();
  });

  it('is created successfully', () => {
    expect(component).toBeTruthy();
  });

  it('closes and returns undefined when "Cancel" button is clicked', () => {
    const cancelButton = fixture.debugElement.query(By.css('#cancel'));
    (cancelButton.nativeElement as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(dialogCloseSpy).toHaveBeenCalledWith(undefined);
  });

  it('closes and returns a string with the added label when "Add" button is clicked',
     () => {
       component.labelInputControl.setValue('newlabel');
       const addButton = fixture.debugElement.query(By.css('#add'));
       (addButton.nativeElement as HTMLButtonElement).click();
       fixture.detectChanges();
       expect(dialogCloseSpy).toHaveBeenCalledWith('newlabel');
     });

  it('closes and returns a string with the added label when on Enter event',
     () => {
       component.labelInputControl.setValue('newlabel');
       const inputForm = fixture.debugElement.query(By.css('form'));
       inputForm.nativeElement.dispatchEvent(
           new KeyboardEvent('keydown', {key: 'Enter', metaKey: true}));
       fixture.detectChanges();
       expect(dialogCloseSpy).toHaveBeenCalledWith('newlabel');
     });

  it('doesn\'t allow adding the same label again', () => {
    component.labelInputControl.setValue('label1');
    const addButton = fixture.debugElement.query(By.css('#add'));
    (addButton.nativeElement as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(dialogCloseSpy).not.toHaveBeenCalled();

    const inputForm = fixture.debugElement.query(By.css('form'));
    inputForm.nativeElement.dispatchEvent(
        new KeyboardEvent('keydown', {key: 'Enter', metaKey: true}));
    fixture.detectChanges();
    expect(dialogCloseSpy).not.toHaveBeenCalled();
  });

  it('emmits unused, possible labels in suggestedLabels$ for the given input',
     (done) => {
       let i = 0;
       component.suggestedLabels$.subscribe(labels => {
         switch (i) {
           case 0:
             expect(labels).toEqual(['unusedlabel']);
             break;
           default:
             expect(labels).toEqual([]);
             done();
         }
         i++;
       });
       component.labelInputControl.setValue('label');
       fixture.detectChanges();
       component.labelInputControl.setValue('label2');
       fixture.detectChanges();
     });

  it('clears options when input is cleared', (done) => {
    let i = 0;
    component.suggestedLabels$.subscribe(labels => {
      switch (i) {
        case 0:
          expect(labels).toEqual(['unusedlabel']);
          break;
        default:
          expect(labels).toEqual([]);
          done();
      }
      i++;
    });
    component.labelInputControl.setValue('label');
    fixture.detectChanges();
    component.labelInputControl.setValue('');
    fixture.detectChanges();
  });

  it('suggests making a new label if the inserted label doesn\'t exist', () => {
    const inputElement =
        fixture.debugElement.query(By.css('input')).nativeElement;
    inputElement.dispatchEvent(new Event('focusin'));
    inputElement.value = 'new different label';
    inputElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const options = overlayContainerElement.querySelectorAll('mat-option');
    expect(options.length).toBe(1);
    expect(options.item(0).textContent)
        .toEqual('Add new label "new different label"');
  });

  it('shows label already present option if the client has the inserted an existing label',
     () => {
       const inputElement =
           fixture.debugElement.query(By.css('input')).nativeElement;
       inputElement.dispatchEvent(new Event('focusin'));
       inputElement.value = 'testlabel';
       inputElement.dispatchEvent(new Event('input'));
       fixture.detectChanges();

       const options = overlayContainerElement.querySelectorAll('mat-option');
       expect(options.length).toBe(1);
       expect(options.item(0).textContent)
           .toEqual('Label "testlabel" already present!');
     });

  it('correctly checks if the inserted label is new', (done) => {
    let i = 0;
    component.isNewLabel$.subscribe(isNew => {
      switch (i) {
        case 0:
          expect(isNew).toEqual(true);
          break;
        case 1:
          expect(isNew).toEqual(false);
          break;
        default:
          expect(isNew).toEqual(true);
          done();
      }
      i++;
    });
    component.labelInputControl.setValue('label');
    fixture.detectChanges();
    component.labelInputControl.setValue('label1');
    fixture.detectChanges();
    component.labelInputControl.setValue('label19');
    fixture.detectChanges();
  });
});
