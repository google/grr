import {OverlayContainer} from '@angular/cdk/overlay';
import {discardPeriodicTasks, fakeAsync, inject, TestBed, tick, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ApiClient, ApiSearchClientResult} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ApiModule} from '@app/lib/api/module';
import {initTestEnvironment} from '@app/testing';
import {of} from 'rxjs';

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
  let httpApiService: jasmine.SpyObj<HttpApiService>;
  let overlayContainer: OverlayContainer;
  let overlayContainerElement: HTMLElement;

  beforeEach(waitForAsync(() => {
    httpApiService = jasmine.createSpyObj('HttpApiService', ['searchClients']);
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,  // This makes test faster and more stable.
            HomeModule,
            ApiModule,
          ],
          providers: [{provide: HttpApiService, useValue: httpApiService}],

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
    const debugElement = fixture.debugElement.query(By.css('input'));
    (debugElement.nativeElement as HTMLInputElement)
        .dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter'}));
    fixture.detectChanges();

    expect(emitSpy).toHaveBeenCalledWith('foo');
  });

  it('does not emit event on enter when query is empty', () => {
    const fixture = TestBed.createComponent(SearchBox);
    // Make sure ngAfterViewInit hook gets processed.
    fixture.detectChanges();

    const componentInstance = fixture.componentInstance;
    const emitSpy = spyOn(componentInstance.querySubmitted, 'emit');

    const debugElement = fixture.debugElement.query(By.css('input'));
    (debugElement.nativeElement as HTMLInputElement)
        .dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter'}));
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
