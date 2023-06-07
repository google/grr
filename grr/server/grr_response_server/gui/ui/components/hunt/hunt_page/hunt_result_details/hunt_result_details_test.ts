import {Component} from '@angular/core';
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
import {HuntResultDetailsGlobalStore} from '../../../../store/hunt_result_details_global_store';
import {HuntResultDetailsGlobalStoreMock, mockHuntResultDetailsGlobalStore} from '../../../../store/hunt_result_details_global_store_test_util';
import {STORE_PROVIDERS} from '../../../../store/store_test_providers';

import {HuntResultDetails} from './hunt_result_details';
import {HuntResultDetailsModule} from './module';
import {HUNT_DETAILS_ROUTES} from './routing';

@Component({template: ''})
class DummyComponent {
}

describe('HuntResultDetails', () => {
  let huntResultDetailsGlobalStore: HuntResultDetailsGlobalStoreMock;
  let activatedRoute: Partial<ActivatedRoute>&
      {paramMap: ReplaySubject<ParamMap>};

  beforeEach(waitForAsync(() => {
    huntResultDetailsGlobalStore = mockHuntResultDetailsGlobalStore();
    activatedRoute = {
      paramMap: new ReplaySubject<ParamMap>(),
    };

    TestBed
        .configureTestingModule({
          imports: [
            ApiModule,
            NoopAnimationsModule,
            HuntResultDetailsModule,
            RouterTestingModule.withRoutes([
              ...HUNT_DETAILS_ROUTES,
              // Mock route for testing source flow link:
              {
                path: 'clients/:clientId/flows/:flowId',
                component: DummyComponent,
              },
            ]),
          ],
          providers: [
            ...STORE_PROVIDERS,
            {
              provide: HuntResultDetailsGlobalStore,
              useFactory: () => huntResultDetailsGlobalStore,
            },
            {provide: ActivatedRoute, useFactory: () => activatedRoute},
          ],
          teardown: {destroyAfterEach: false}
        })
        .compileComponents();

    TestBed.inject(Router);
  }));

  describe('Route params', () => {
    it('query store based on route', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      activatedRoute.paramMap.next(
          convertToParamMap({'key': 'C.123-5678-999999999999'}));

      expect(huntResultDetailsGlobalStore.selectHuntResultId)
          .toHaveBeenCalledWith('C.123-5678-999999999999', undefined);
    });

    it('query store based on route with type', () => {
      activatedRoute.paramMap.next(convertToParamMap({
        'key': 'C.123-5678-999999999999',
        'payloadType': 'FileFinderResult',
      }));
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      expect(huntResultDetailsGlobalStore.selectHuntResultId)
          .toHaveBeenCalledWith('C.123-5678-999999999999', 'FileFinderResult');
    });
  });

  describe('Overview', () => {
    it('displays hunt Id information from store', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      huntResultDetailsGlobalStore.mockedObservables.huntId$.next('123');

      fixture.detectChanges();

      expect(fixture.nativeElement.innerText).toContain('123');
    });

    it('displays timestamp information from store', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);

      huntResultDetailsGlobalStore.mockedObservables.timestamp$.next(
          new Date('1970-01-12 13:46:39 UTC'));

      fixture.detectChanges();

      const timestamp = fixture.debugElement.query(By.css('app-timestamp'));
      expect(timestamp.nativeElement.innerText)
          .toContain('1970-01-12 13:46:39 UTC');
    });

    it('displays client Id information from store', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      huntResultDetailsGlobalStore.mockedObservables.clientId$.next('C.123');

      fixture.detectChanges();

      expect(fixture.nativeElement.innerText).toContain('C.123');
    });

    describe('source flow link', () => {
      it('displays the link', () => {
        const fixture = TestBed.createComponent(HuntResultDetails);
        fixture.detectChanges();

        huntResultDetailsGlobalStore.mockedObservables.clientId$.next('C.123');
        huntResultDetailsGlobalStore.mockedObservables.huntId$.next('123ABCD');

        fixture.detectChanges();

        const sourceFlowLink =
            fixture.debugElement.query(By.css('a[name=\'sourceFlow\']'));

        expect(sourceFlowLink).toBeTruthy();

        // Note (pascuals): I haven't been able to get the `href` attribute
        // to be correctly populated when multiple `outlet` instances are
        // passed to a [routerLink] directive. It would be good to revisit it:

        // expect(sourceFlowLink.nativeElement.href)
        //     .toContain('/clients/C.123/flows/123ABCD');
      });

      it('displays "Unknown" when no huntId and clientId available', () => {
        const fixture = TestBed.createComponent(HuntResultDetails);
        fixture.detectChanges();

        huntResultDetailsGlobalStore.mockedObservables.clientId$.next('');
        huntResultDetailsGlobalStore.mockedObservables.huntId$.next('');

        fixture.detectChanges();

        const sourceFlowLink =
            fixture.debugElement.query(By.css('[name=\'sourceFlow\']'));

        expect(sourceFlowLink).toBeNull();

        const overview =
            fixture.debugElement.query(By.css('[name=\'unknownFlow\']'));

        expect(overview.nativeElement.textContent).toContain('Unknown');
      });

      it('displays the hunt Id when no clientId available', () => {
        const fixture = TestBed.createComponent(HuntResultDetails);
        fixture.detectChanges();

        huntResultDetailsGlobalStore.mockedObservables.clientId$.next('');
        huntResultDetailsGlobalStore.mockedObservables.huntId$.next('123ABCD');

        fixture.detectChanges();

        const sourceFlowLink =
            fixture.debugElement.query(By.css('[name=\'sourceFlow\']'));

        expect(sourceFlowLink).toBeNull();

        const overview =
            fixture.debugElement.query(By.css('[name=\'unknownFlow\']'));

        expect(overview.nativeElement.textContent).toContain('123ABCD');
      });
    });

    it('displays result payload information from store', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      huntResultDetailsGlobalStore.mockedObservables.resultOrErrorDisplay$.next(
          `{'something': 'is coming'}`);

      fixture.detectChanges();

      const payload = fixture.debugElement.query(By.css('[name=\'rawData\']'));
      expect(payload.nativeElement.innerText)
          .toContain(`{'something': 'is coming'}`);
    });

    it('displays flow information from store', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      huntResultDetailsGlobalStore.mockedObservables.flowWithDescriptor$.next({
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
        descriptor: newFlowDescriptor({
          name: 'SomeFlow',
          friendlyName: `Some
                Flow`
        }),
        flowArgType: 'foo',
      });
      fixture.detectChanges();

      const flowDetailsCard =
          fixture.debugElement.query(By.css('flow-details'));
      expect(flowDetailsCard).toBeTruthy();

      expect(flowDetailsCard.nativeElement.innerText).toContain('Some Flow');
      expect(flowDetailsCard.nativeElement.innerText).toContain('person');
      expect(flowDetailsCard.nativeElement.innerText).toContain('5678');
    });

    it('displays raw error information from store', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      huntResultDetailsGlobalStore.mockedObservables.resultOrErrorDisplay$.next(
          `{
        logMessage: 'oof',
        backtrace: 'this is tough',
      }`);
      fixture.detectChanges();

      const rawError = fixture.debugElement.query(By.css('[name=\'rawData\']'));

      expect(rawError.nativeElement.innerText).toContain('oof');
      expect(rawError.nativeElement.innerText).toContain('this is tough');
    });

    it('displays error message if no raw data available', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      const rawError = fixture.debugElement.query(By.css('[name=\'rawData\']'));

      expect(rawError.nativeElement.innerText).toContain('Data not found');
    });
  });

  describe('Loading states', () => {
    it('displays a loading spinner if a hunt result is being loaded', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      huntResultDetailsGlobalStore.mockedObservables.isHuntResultLoading$.next(
          true);
      fixture.detectChanges();

      const overview =
          fixture.debugElement.query(By.css('[name=\'overview\']'));

      expect(overview).toBeNull();

      const loadingSpinner = fixture.debugElement.query(By.css('mat-spinner'));
      expect(loadingSpinner).toBeTruthy();
    });

    it('displays a loading spinner if a hunt result is being loaded', () => {
      const fixture = TestBed.createComponent(HuntResultDetails);
      fixture.detectChanges();

      huntResultDetailsGlobalStore.mockedObservables.isFlowLoading$.next(true);
      fixture.detectChanges();

      const overview =
          fixture.debugElement.query(By.css('[name=\'overview\']'));

      expect(overview).toBeTruthy();

      const flowLoadingSpinner =
          fixture.debugElement.query(By.css('.flow-loading-spinner'));
      expect(flowLoadingSpinner).toBeTruthy();
    });
  });
});
