import {async, TestBed, ComponentFixture, inject} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';
import {By} from '@angular/platform-browser';
import {ClientAddLabelDialogModule} from './module';
import {ClientAddLabelDialog} from './client_add_label_dialog';
import {ReactiveFormsModule} from '@angular/forms';
import {MatDialogModule, MAT_DIALOG_DATA, MatDialogRef} from '@angular/material/dialog';
import {ClientLabel} from '@app/lib/models/client';
import {ConfigFacade} from '@app/store/config_facade';
import {mockConfigFacade, ConfigFacadeMock} from '@app/store/config_facade_test_util';

initTestEnvironment();

describe('Client Add Label Dialog', () => {
  let fixture: ComponentFixture<ClientAddLabelDialog>;
  let component: ClientAddLabelDialog;
  const clientLabels: ReadonlyArray<ClientLabel> = [
    {owner: '', name: 'label1'},
    {owner: '', name: 'testlabel'}
  ];

  let configFacadeMock: ConfigFacadeMock;
  let dialogCloseSpy: jasmine.Spy;

  beforeEach(async(() => {
    configFacadeMock = mockConfigFacade();

    TestBed
      .configureTestingModule({
        declarations: [ClientAddLabelDialog],
        imports: [
          ClientAddLabelDialogModule,
          NoopAnimationsModule,  // This makes test faster and more stable.
          ReactiveFormsModule,
          MatDialogModule,
        ],
        providers: [
          {provide: MatDialogRef, useValue: {close(value: string | undefined) {} }},
          {provide: MAT_DIALOG_DATA, useValue: clientLabels},
          {provide: ConfigFacade, useValue: configFacadeMock}
        ],
      })
      .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(ClientAddLabelDialog);
    component = fixture.componentInstance;
    dialogCloseSpy = spyOn(component.dialogRef, 'close');
    configFacadeMock.clientsLabelsSubject.next([
      {owner: '', name: 'label1'},
      {owner: '', name: 'unusedlabel'},
      {owner: '', name: 'testlabel'},
    ])
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

  it('closes and returns a string with the added label when "Add" button is clicked', () => {
    component.labelInputControl.setValue('newlabel');
    const addButton = fixture.debugElement.query(By.css('#add'));
    (addButton.nativeElement as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(dialogCloseSpy).toHaveBeenCalledWith('newlabel');
  });

  it('closes and returns a string with the added label when on Enter event', () => {
    component.labelInputControl.setValue('newlabel');
    const inputForm = fixture.debugElement.query(By.css('input'));
    (inputForm.nativeElement as HTMLInputElement)
      .dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter'}));
    fixture.detectChanges();
    expect(dialogCloseSpy).toHaveBeenCalledWith('newlabel');
  });

  it('doesn\'t allow adding the same label again', () => {
    component.labelInputControl.setValue('label1');
    const addButton = fixture.debugElement.query(By.css('#add'));
    (addButton.nativeElement as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(dialogCloseSpy).not.toHaveBeenCalled();

    const inputForm = fixture.debugElement.query(By.css('input'));
    (inputForm.nativeElement as HTMLInputElement)
      .dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter'}));
    fixture.detectChanges();
    expect(dialogCloseSpy).not.toHaveBeenCalled();
  });

  it('updates existing labels list upon input change', (done) => {
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
});
