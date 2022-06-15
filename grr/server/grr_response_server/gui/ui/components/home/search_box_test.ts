import {OverlayContainer} from '@angular/cdk/overlay';
import {discardPeriodicTasks, fakeAsync, inject, TestBed, tick} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {of} from 'rxjs';

import {ApiClient, ApiSearchClientResult} from '../../lib/api/api_interfaces';
import {HttpApiService} from '../../lib/api/http_api_service';
import {HttpApiServiceMock, mockHttpApiService} from '../../lib/api/http_api_service_test_util';
import {ApiModule} from '../../lib/api/module';
import {ConfigGlobalStore} from '../../store/config_global_store';
import {ConfigGlobalStoreMock, mockConfigGlobalStore} from '../../store/config_global_store_test_util';
import {initTestEnvironment} from '../../testing';

import {HomeModule} from './module';
import {SearchBox} from './search_box';


initTestEnvironment();

const apiClients: ReadonlyArray<ApiClient> = [
  {
    clientId: 'C.1234',
    knowledgeBase: {
      fqdn: 'foo',
      os: 'Linux',
    },
    lastSeenAt: '1571789996679000',
    labels: [],
    age: '1571789996679000',
  },
  {
    clientId: 'C.1234',
    knowledgeBase: {
      fqdn: 'bar',
      os: 'Linux',
    },
    lastSeenAt: '1571789996679000',
    labels: [],
    age: '1571789996679000',
  },
  {
    clientId: 'C.1234',
    knowledgeBase: {
      fqdn: 'foobar',
      os: 'Linux',
    },
    lastSeenAt: '1571789996679000',
    labels: [],
    age: '1571789996679000',
  }
];

describe('SearchBox Component', () => {
  let httpApiService: HttpApiServiceMock;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;
  let configGlobalStore: ConfigGlobalStoreMock;

  beforeEach(() => {
    httpApiService = mockHttpApiService();
    configGlobalStore = mockConfigGlobalStore();

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            HomeModule,
            ApiModule,
          ],
          providers: [
            {provide: HttpApiService, useValue: httpApiService},
            {provide: ConfigGlobalStore, useFactory: () => configGlobalStore}
          ],
          teardown: {destroyAfterEach: false}
        })
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

  it('emits event when query is typed and Enter is pressed', () => {
    const fixture = TestBed.createComponent(SearchBox);
    // Make sure ngAfterViewInit hook gets processed.
    fixture.detectChanges();

    const componentInstance = fixture.componentInstance;
    const emitSpy = spyOn(componentInstance.querySubmitted, 'emit');

    componentInstance.inputFormControl.setValue('foo');
    fixture.debugElement.query(By.css('form'))
        .nativeElement.dispatchEvent(
            new KeyboardEvent('keypress', {key: 'Enter'}));
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

  it('populates client search results', fakeAsync(() => {
       const fixture = TestBed.createComponent(SearchBox);
       // Make sure ngAfterViewInit hook gets processed.
       fixture.detectChanges();

       const searchResults: ApiSearchClientResult = {items: apiClients};
       httpApiService.searchClients.and.returnValue(of(searchResults));

       const inputElement =
           fixture.debugElement.query(By.css('input')).nativeElement;
       inputElement.dispatchEvent(new Event('focusin'));
       inputElement.value = 'foo';
       inputElement.dispatchEvent(new Event('input'));

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

       const searchResults: ApiSearchClientResult = {items: []};
       httpApiService.searchClients.and.returnValue(of(searchResults));

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
