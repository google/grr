import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {MatMenuHarness} from '@angular/material/menu/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {ConfigGlobalStore} from '../../../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../../../testing';

import {ClientsForm} from './clients_form';
import {ClientsFormModule} from './module';

initTestEnvironment();

describe('clients form test', () => {
  let configGlobalStoreMock: ConfigGlobalStoreMock;
  beforeEach(waitForAsync(() => {
    configGlobalStoreMock = mockConfigGlobalStore();
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ClientsFormModule,
          ],
          providers: [{
            provide: ConfigGlobalStore,
            useFactory: () => configGlobalStoreMock
          }],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();
  }));

  it('toggles contents on click on toggle button', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    const button = fixture.debugElement.query(By.css('#client-form-toggle'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('opens contents on click on header', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    const button = fixture.debugElement.query(By.css('#client-form-toggle'));
    fixture.detectChanges();

    expect(fixture.componentInstance.hideContent).toBeFalse();

    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeTrue();

    const header = fixture.debugElement.query(By.css('.header'));
    header.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    expect(fixture.componentInstance.hideContent).toBeFalse();
  });

  it('only renders the match button when there are several conditions',
     async () => {
       const fixture = TestBed.createComponent(ClientsForm);
       fixture.detectChanges();
       expect(fixture.debugElement.query(By.css('.match-condition')))
           .toBeNull();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const menu = await loader.getHarness(MatMenuHarness);
       await menu.open();
       const items = await menu.getItems();
       await items[0].click();
       expect(fixture.debugElement.query(By.css('.match-condition')))
           .not.toBeNull();
     });

  it('renders an os form by default', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Operating System');
  });

  it('deletes the form when clicking cancel', () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();
    const before = fixture.debugElement.nativeElement.textContent;
    expect(before).toContain('Operating System');

    const button = fixture.debugElement.query(By.css('#close'));
    button.triggerEventHandler('click', new MouseEvent('click'));
    fixture.detectChanges();
    const after = fixture.debugElement.nativeElement.textContent;
    expect(after).not.toContain('Operating System');
  });

  it('adds a label form when clicking on Label in menu', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[1].click();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Label');
    expect(fixture.componentInstance.conditions().controls.length).toBe(2);
  });

  it('adds and deletes label name input when clicking on add and delete button',
     async () => {
       const fixture = TestBed.createComponent(ClientsForm);
       fixture.detectChanges();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const menu = await loader.getHarness(MatMenuHarness);
       await menu.open();
       const items = await menu.getItems();
       await items[1].click();
       const text = fixture.debugElement.nativeElement.textContent;
       expect(text).toContain('Label');
       expect(fixture.componentInstance.conditions().controls.length).toBe(2);
       expect(fixture.componentInstance.labelNames(1).controls.length).toBe(1);
       const button = fixture.debugElement.query(By.css('#add-label-name'));
       button.triggerEventHandler('click', new MouseEvent('click'));
       fixture.detectChanges();
       expect(fixture.componentInstance.labelNames(1).controls.length).toBe(2);
       const deleteButton =
           fixture.debugElement.query(By.css('#remove-label-name'));
       deleteButton.triggerEventHandler('click', new MouseEvent('click'));
       fixture.detectChanges();
       expect(fixture.componentInstance.labelNames(1).controls.length).toBe(1);
     });

  it('adds a integer form when clicking on Client Clock in menu', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[4].click();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Client Clock');
    expect(fixture.debugElement.query(By.css('.operator'))).not.toBeNull();
    expect(fixture.componentInstance.conditions().controls.length).toBe(2);
  });

  it('adds a regex form when clicking on Client Description in menu',
     async () => {
       const fixture = TestBed.createComponent(ClientsForm);
       fixture.detectChanges();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const menu = await loader.getHarness(MatMenuHarness);
       await menu.open();
       const items = await menu.getItems();
       await items[5].click();
       const text = fixture.debugElement.nativeElement.textContent;
       expect(text).toContain('Client Description');
       expect(fixture.debugElement.query(By.css('.attribute-regex')))
           .not.toBeNull();
       expect(fixture.componentInstance.conditions().controls.length).toBe(2);
     });

  it('builds correct rule set using the form values', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[5].click();
    const text = fixture.debugElement.nativeElement.textContent;
    expect(text).toContain('Client Description');
    expect(fixture.debugElement.query(By.css('.attribute-regex')))
        .not.toBeNull();
    expect(fixture.componentInstance.conditions().controls.length).toBe(2);
  });

  it('shows autocomplete options correctly', async () => {
    const fixture = TestBed.createComponent(ClientsForm);
    fixture.detectChanges();

    configGlobalStoreMock.mockedObservables.clientsLabels$.next([
      'label1',
      'unusedlabel',
      'testlabel',
    ]);
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const menu = await loader.getHarness(MatMenuHarness);
    await menu.open();
    const items = await menu.getItems();
    await items[1].click();
    const labelName = fixture.debugElement.query(By.css('.label-name'))
                          .query(By.css('input'));
    labelName.nativeElement.dispatchEvent(new Event('focusin'));
    fixture.detectChanges();
    expect(fixture.debugElement.queryAll(By.css('.mat-option')).length).toBe(3);
    expect(fixture.debugElement.queryAll(By.css('.mat-option'))[0]
               .nativeElement.textContent)
        .toContain('label1');
  });
});
