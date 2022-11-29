import {OverlayContainer} from '@angular/cdk/overlay';
import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {discardPeriodicTasks, fakeAsync, inject, TestBed, tick} from '@angular/core/testing';
import {ReactiveFormsModule} from '@angular/forms';
import {MatInputHarness} from '@angular/material/input/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {HttpApiService} from '../../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../../lib/api/http_api_service_test_util';
import {ApiModule} from '../../lib/api/module';
import {Client} from '../../lib/models/client';
import {newClient} from '../../lib/models/model_test_util';
import {ClientSearchLocalStore} from '../../store/client_search_local_store';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {injectMockStore} from '../../store/store_test_providers';
import {mockStore} from '../../store/store_test_util';
import {initTestEnvironment} from '../../testing';
import {HomeModule} from '../home/module';

import {SearchBox} from './search_box';


initTestEnvironment();

const CLIENTS: readonly Client[] = [
  newClient({}),
  newClient({}),
  newClient({}),
];

describe('SearchBox Component', () => {
  let httpApiService: HttpApiServiceMock;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    configGlobalStore = mockConfigGlobalStore();
    const clientSearchLocalStore = mockStore(ClientSearchLocalStore);

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HomeModule,
            ReactiveFormsModule,
            ApiModule,
          ],
          providers: [
            {provide: HttpApiService, useValue: httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore},
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            ClientSearchLocalStore, {useFactory: () => clientSearchLocalStore})
        .compileComponents();

    inject([OverlayContainer], (oc: OverlayContainer) => {
      overlayContainer = oc;
      overlayContainerElement = oc.getContainerElement();
    })();
  });

  afterEach(() => {
    overlayContainer.ngOnDestroy();
  });

  it('creates the component', () => {
    const fixture = TestBed.createComponent(SearchBox);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('emits event when query is typed and Enter is pressed', async () => {
    const fixture = TestBed.createComponent(SearchBox);
    // Make sure ngAfterViewInit hook gets processed.
    fixture.detectChanges();

    const componentInstance = fixture.componentInstance;
    const emitSpy = spyOn(componentInstance.querySubmitted, 'emit');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const inputHarness = await harnessLoader.getHarness(
        MatInputHarness.with({selector: 'input'}));
    await inputHarness.setValue('foo');

    const form = fixture.debugElement.query(By.css('form')).nativeElement;
    form.dispatchEvent(new KeyboardEvent('keypress', {key: 'Enter'}));

    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith('foo');
  });

  it('does not emit event on enter when query is empty', () => {
    const fixture = TestBed.createComponent(SearchBox);
    // Make sure ngAfterViewInit hook gets processed.
    fixture.detectChanges();

    const componentInstance = fixture.componentInstance;
    const emitSpy = spyOn(componentInstance.querySubmitted, 'emit');

    fixture.debugElement.query(By.css('form'))
        .nativeElement.dispatchEvent(
            new KeyboardEvent('keypress', {key: 'Enter'}));
    fixture.detectChanges();

    expect(emitSpy).not.toHaveBeenCalled();
  });

  it('populates client search results', fakeAsync(async () => {
       const fixture = TestBed.createComponent(SearchBox);
       // Make sure ngAfterViewInit hook gets processed.
       fixture.detectChanges();

       const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
       const input = await harnessLoader.getHarness(
           MatInputHarness.with({selector: 'input'}));
       await input.setValue('foo');
       await input.blur();

       injectMockStore(ClientSearchLocalStore)
           .mockedObservables.clients$.next(CLIENTS);

       fixture.detectChanges();
       // Move clock ahead to trigger debounce period.
       tick(350);
       fixture.detectChanges();
       // Remove period timer resulting from the tick call.
       discardPeriodicTasks();

       const options = overlayContainerElement.querySelectorAll('mat-option');
       expect(options.length).toBe(3);
     }));

  it('includes labels in client search results, for matching query',
     fakeAsync(() => {
       const fixture = TestBed.createComponent(SearchBox);
       // All client labels fetched from server.
       configGlobalStore.mockedObservables.clientsLabels$.next([
         'test1',
         'test2',
         'other',
       ]);
       // Make sure ngAfterViewInit hook gets processed.
       fixture.detectChanges();

       injectMockStore(ClientSearchLocalStore)
           .mockedObservables.clients$.next([]);

       const inputElement =
           fixture.debugElement.query(By.css('input')).nativeElement;
       inputElement.dispatchEvent(new Event('focusin'));
       inputElement.value = 'label:t';
       inputElement.dispatchEvent(new Event('input'));

       fixture.detectChanges();
       // Move clock ahead to trigger debounce period.
       tick(350);
       fixture.detectChanges();
       // Remove period timer resulting from the tick call.
       discardPeriodicTasks();

       const options = overlayContainerElement.querySelectorAll('mat-option');
       // Should only show labels matching query (test1 and test2).
       expect(options.length).toBe(2);
     }));

  it('emits event on client search results option selected', () => {
    const fixture = TestBed.createComponent(SearchBox);
    // Make sure ngAfterViewInit hook gets processed.
    fixture.detectChanges();

    const emitSpy = spyOn(fixture.componentInstance.querySubmitted, 'emit');

    const matAutoCompleteElement =
        fixture.debugElement.query(By.css('mat-autocomplete'));
    matAutoCompleteElement.triggerEventHandler(
        'optionSelected', {option: {value: 'foo'}});

    expect(emitSpy).toHaveBeenCalledWith('foo');
  });
});
