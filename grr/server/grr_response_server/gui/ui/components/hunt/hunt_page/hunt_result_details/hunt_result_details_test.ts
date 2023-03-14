import {TestBed, waitForAsync} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ActivatedRoute, convertToParamMap, ParamMap, Router} from '@angular/router';
import {RouterTestingModule} from '@angular/router/testing';
import {ReplaySubject} from 'rxjs';

import {ApiFlowState} from '../../../../lib/api/api_interfaces';
import {ApiModule} from '../../../../lib/api/module';
import {translateFlow} from '../../../../lib/api_translation/flow';
import {newFlowDescriptor} from '../../../../lib/models/model_test_util';
import {HuntPageGlobalStore} from '../../../../store/hunt_page_global_store';
import {HuntPageGlobalStoreMock, mockHuntPageGlobalStore} from '../../../../store/hunt_page_global_store_test_util';
import {STORE_PROVIDERS} from '../../../../store/store_test_providers';

import {HuntResultDetails} from './hunt_result_details';
import {HuntResultDetailsModule} from './module';
import {HUNT_DETAILS_ROUTES} from './routing';

describe('hunt details', () => {
  let huntPageGlobalStore: HuntPageGlobalStoreMock;
  let activatedRoute: Partial<ActivatedRoute>&
      {paramMap: ReplaySubject<ParamMap>};

  beforeEach(waitForAsync(() => {
    huntPageGlobalStore = mockHuntPageGlobalStore();
    activatedRoute = {
      paramMap: new ReplaySubject<ParamMap>(),
    };

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            HuntResultDetailsModule,
            RouterTestingModule.withRoutes(HUNT_DETAILS_ROUTES),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {
              provide: HuntPageGlobalStore,
              useFactory: () => huntPageGlobalStore,
            },
            {provide: ActivatedRoute, useFactory: () => activatedRoute},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    TestBed.inject(Router);
  }));

  it('query store based on route', () => {
    activatedRoute.paramMap.next(
        convertToParamMap({'key': 'C.123-5678-999999999999'}));
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    expect(huntPageGlobalStore.selectResult)
        .toHaveBeenCalledWith('C.123-5678-999999999999');
  });

  it('displays overview information from store', () => {
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntResultId$.next(
        'C.123-5678-999999999999');
    huntPageGlobalStore.mockedObservables.selectedHuntResult$.next({
      clientId: 'C.123',
      timestamp: '999999999999',
      payload: {'something': 'is coming'}
    });
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('C.123');

    const overview = fixture.debugElement.query(By.css('[name=\'overview\']'));
    expect(overview.nativeElement.innerText).toContain('5678');
    expect(overview.nativeElement.innerText)
        .toContain('1970-01-12 13:46:39 UTC');
  });

  it('displays flow information from store', () => {
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntResultId$.next(
        'C.123-5678-999999999999');
    huntPageGlobalStore.mockedObservables.selectedResultFlowWithDescriptor$
        .next({
          flow: translateFlow({
            flowId: '5678',
            clientId: 'C.123',
            name: 'SomeFlow',
            creator: 'person',
            lastActiveAt: '1234',
            startedAt: '1234',
            state: ApiFlowState.RUNNING,
            isRobot: false,
          }),
          descriptor:
              newFlowDescriptor({name: 'SomeFlow', friendlyName: 'Some Flow'}),
          flowArgType: 'foo',
        });
    fixture.detectChanges();

    const flowDetailsCard = fixture.debugElement.query(By.css('flow-details'));
    expect(flowDetailsCard).toBeTruthy();

    expect(flowDetailsCard.nativeElement.innerText).toContain('Some Flow');
    expect(flowDetailsCard.nativeElement.innerText).toContain('person');
    expect(flowDetailsCard.nativeElement.innerText).toContain('5678');
  });

  it('displays raw result information from store', () => {
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntResultId$.next(
        'C.123-5678-999999999999');
    huntPageGlobalStore.mockedObservables.selectedHuntResult$.next({
      clientId: 'C.123',
      timestamp: '999999999999',
      payload: {'something': 'is coming'}
    });
    fixture.detectChanges();

    const rawResult = fixture.debugElement.query(By.css('[name=\'rawData\']'));

    expect(rawResult.nativeElement.innerText).toContain('something');
    expect(rawResult.nativeElement.innerText).toContain('is coming');
  });

  it('displays raw error information from store', () => {
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntResultId$.next(
        'C.123-5678-999999999999');
    huntPageGlobalStore.mockedObservables.selectedHuntError$.next({
      clientId: 'C.123',
      timestamp: '999999999999',
      logMessage: 'oof',
      backtrace: 'this is tough',
    });
    fixture.detectChanges();

    const rawError = fixture.debugElement.query(By.css('[name=\'rawData\']'));

    expect(rawError.nativeElement.innerText).toContain('oof');
    expect(rawError.nativeElement.innerText).toContain('this is tough');
  });

  it('displays error message if no raw data available', () => {
    const fixture = TestBed.createComponent(HuntResultDetails);
    fixture.detectChanges();

    huntPageGlobalStore.mockedObservables.selectedHuntResultId$.next(
        'C.123-5678-999999999999');
    huntPageGlobalStore.mockedObservables.selectedHuntResult$.next(null);
    huntPageGlobalStore.mockedObservables.selectedHuntError$.next(null);
    fixture.detectChanges();

    const rawError = fixture.debugElement.query(By.css('[name=\'rawData\']'));

    expect(rawError.nativeElement.innerText).toContain('Data not found');
  });
});
