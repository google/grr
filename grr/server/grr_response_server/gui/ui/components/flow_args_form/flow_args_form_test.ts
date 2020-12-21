import {Component, Input, ViewChild} from '@angular/core';
import {fakeAsync, TestBed, tick} from '@angular/core/testing';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {FlowArgsFormModule} from '@app/components/flow_args_form/module';
import {ApiModule} from '@app/lib/api/module';
import {initTestEnvironment} from '@app/testing';
import {ReplaySubject, Subject} from 'rxjs';

import {CollectBrowserHistoryArgs, CollectBrowserHistoryArgsBrowser, GlobComponentExplanation} from '../../lib/api/api_interfaces';
import {FlowDescriptor} from '../../lib/models/flow';
import {newClient} from '../../lib/models/model_test_util';
import {ExplainGlobExpressionService} from '../../lib/service/explain_glob_expression_service/explain_glob_expression_service';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ClientPageFacadeMock, mockClientPageFacade} from '../../store/client_page_facade_test_util';

import {FlowArgsForm} from './flow_args_form';


initTestEnvironment();

const TEST_FLOW_DESCRIPTORS = Object.freeze({
  CollectBrowserHistory: {
    name: 'CollectBrowserHistory',
    friendlyName: 'Browser History',
    category: 'Browser',
    defaultArgs: {
      browsers: [CollectBrowserHistoryArgsBrowser.CHROME],
    },
  },
  CollectSingleFile: {
    name: 'CollectSingleFile',
    friendlyName: 'Collect Single File',
    category: 'Filesystem',
    defaultArgs: {
      path: '/foo',
      maxSizeBytes: 1024,
    },
  },
  CollectMultipleFiles: {
    name: 'CollectMultipleFiles',
    friendlyName: 'Collect Multiple Files',
    category: 'Filesystem',
    defaultArgs: {
      pathExpressions: [],
    },
  },
});


@Component({
  template:
      '<flow-args-form [flowDescriptor]="flowDescriptor"></flow-args-form>',
})
class TestHostComponent {
  @Input() flowDescriptor?: FlowDescriptor;
  @ViewChild(FlowArgsForm) flowArgsForm!: FlowArgsForm;
}

function setUp() {
  return TestBed
      .configureTestingModule({
        imports: [
          NoopAnimationsModule,
          ApiModule,
          FlowArgsFormModule,
        ],
        declarations: [
          TestHostComponent,
        ],

      })
      .compileComponents();
}

describe('FlowArgsForm Component', () => {
  beforeEach(setUp);

  it('is empty initially', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.innerText.trim()).toEqual('');
  });

  it('renders sub-form correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.CollectBrowserHistory;
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain('Chrome');
  });

  it('emits form value changes', (done) => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    let counter = 0;

    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe((value) => {
      const args = value as CollectBrowserHistoryArgs;
      if (counter === 0) {
        expect((args.browsers ??
                []).indexOf(CollectBrowserHistoryArgsBrowser.CHROME))
            .not.toBe(-1);
        counter++;
      } else {
        expect((args.browsers ??
                []).indexOf(CollectBrowserHistoryArgsBrowser.CHROME))
            .toBe(-1);
        done();
      }
    });

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.CollectBrowserHistory;
    fixture.detectChanges();

    // This test assumes that the first label in the CollectBrowserHistoryForm
    // is Chrome, which is not ideal, but an effective workaround.
    const label = fixture.debugElement.query(By.css('label')).nativeElement;
    expect(label.innerText).toContain('Chrome');
    label.click();
    fixture.detectChanges();
  });

  it('is empty after flow unselection', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.CollectBrowserHistory;
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor = undefined;
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText.trim()).toEqual('');
  });

  it('fallback form emits defaultArgs', (done) => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.flowDescriptor = {
      name: 'FlowWithoutForm',
      friendlyName: '---',
      category: 'Misc',
      defaultArgs: {foo: 42},
    };
    fixture.detectChanges();

    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(values => {
      expect(values).toEqual({foo: 42});
      done();
    });
  });

  it('emits valid:false when form input is invalid', (done) => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.CollectSingleFile;
    fixture.detectChanges();

    const byteInput = fixture.debugElement.query(By.css('input[byteInput]'));
    byteInput.nativeElement.value = 'invalid';
    byteInput.triggerEventHandler('change', {target: byteInput.nativeElement});
    fixture.detectChanges();

    fixture.componentInstance.flowArgsForm.valid$.subscribe((valid) => {
      expect(valid).toBeFalse();
      done();
    });
  });
});


Object.values(TEST_FLOW_DESCRIPTORS).forEach(fd => {
  describe(`FlowArgForm ${fd.name}`, () => {
    beforeEach(setUp);

    it('renders a sub-form', () => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      fixture.componentInstance.flowDescriptor = fd;
      fixture.detectChanges();

      expect(fixture.nativeElement.innerText.trim()).toBeTruthy();
    });

    it('emits initial form values', (done) => {
      const fixture = TestBed.createComponent(TestHostComponent);
      fixture.detectChanges();

      fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
          values => {
            expect(values).toBeTruthy();
            done();
          });

      fixture.componentInstance.flowDescriptor = fd;
      fixture.detectChanges();
    });
  });
});

describe(`FlowArgForm CollectSingleFile`, () => {
  beforeEach(setUp);

  it('explains the byte input size', () => {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.CollectSingleFile;
    fixture.detectChanges();

    // Verify that defaultFlowArgs are rendered properly as hint.
    let text = fixture.debugElement.nativeElement.innerText;
    expect(text).toContain('1,024 bytes');

    const byteInput = fixture.debugElement.query(By.css('input[byteInput]'));
    byteInput.nativeElement.value = '2 kib';
    byteInput.triggerEventHandler('change', {target: byteInput.nativeElement});
    fixture.detectChanges();

    text = fixture.debugElement.nativeElement.innerText;
    expect(text).toContain('2 kibibytes ');
    expect(text).toContain('2,048 bytes');
  });
});

describe(`FlowArgForm CollectMultipleFiles`, () => {
  let clientPageFacade: ClientPageFacadeMock;
  let explainGlobExpressionService: Partial<ExplainGlobExpressionService>;
  let explanation$: Subject<ReadonlyArray<GlobComponentExplanation>>;

  beforeEach(() => {
    clientPageFacade = mockClientPageFacade();
    explanation$ = new ReplaySubject(1);
    explainGlobExpressionService = {
      explanation$,
      explain: jasmine.createSpy('explain'),
    };
    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            ApiModule,
            FlowArgsFormModule,
          ],
          declarations: [
            TestHostComponent,
          ],

          providers: [
            {provide: ClientPageFacade, useFactory: () => clientPageFacade},
          ],
        })
        // Override ALL providers, because each path expression input provides
        // its own ExplainGlobExpressionService. The above way only overrides
        // the root-level.
        .overrideProvider(
            ExplainGlobExpressionService,
            {useFactory: () => explainGlobExpressionService})
        .compileComponents();
  });

  function prepareFixture() {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    clientPageFacade.selectedClientSubject.next(newClient({
      clientId: 'C.1234',
    }));

    fixture.componentInstance.flowDescriptor =
        TEST_FLOW_DESCRIPTORS.CollectMultipleFiles;
    fixture.detectChanges();

    return fixture;
  }

  it('calls the Facade to explain GlobExpressions', fakeAsync(() => {
       const fixture = prepareFixture();

       const input = fixture.debugElement.query(By.css('input')).nativeElement;
       input.value = '/home/{foo,bar}';
       input.dispatchEvent(new Event('input'));

       tick(1000);
       fixture.detectChanges();

       expect(explainGlobExpressionService.explain)
           .toHaveBeenCalledWith('C.1234', '/home/{foo,bar}');
     }));

  it('shows the loaded GlobExpressionExplanation', () => {
    const fixture = prepareFixture();

    explanation$.next([
      {globExpression: '/home/'},
      {globExpression: '{foo,bar}', examples: ['foo', 'bar']},
    ]);
    fixture.detectChanges();

    const text = fixture.debugElement.nativeElement.innerText;
    expect(text).toContain('/home/foo');
  });

  it('allows adding path expressions', (done) => {
    const fixture = prepareFixture();

    let inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(1);

    const addButton =
        fixture.debugElement.query(By.css('#button-add-path-expression'));
    addButton.nativeElement.click();
    fixture.detectChanges();

    inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(2);

    inputs[0].nativeElement.value = '/0';
    inputs[0].nativeElement.dispatchEvent(new Event('input'));

    inputs[1].nativeElement.value = '/1';
    inputs[1].nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
        (values) => {
          expect(values).toEqual({pathExpressions: ['/0', '/1']});
          done();
        });
  });

  it('allows removing path expressions', (done) => {
    const fixture = prepareFixture();

    let inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(1);

    const addButton =
        fixture.debugElement.query(By.css('#button-add-path-expression'));
    addButton.nativeElement.click();
    fixture.detectChanges();

    inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(2);

    inputs[0].nativeElement.value = '/0';
    inputs[0].nativeElement.dispatchEvent(new Event('input'));

    inputs[1].nativeElement.value = '/1';
    inputs[1].nativeElement.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const removeButtons =
        fixture.debugElement.queryAll(By.css('button[aria-label=\'Remove\']'));
    expect(removeButtons.length).toEqual(2);

    removeButtons[1].nativeElement.click();
    fixture.detectChanges();

    inputs = fixture.debugElement.queryAll(By.css('input'));
    expect(inputs.length).toEqual(1);

    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
        (values) => {
          expect(values).toEqual({pathExpressions: ['/0']});
          done();
        });
  });

  it('allows adding modification time expression', (done) => {
    const fixture = prepareFixture();

    const conditionButton =
        fixture.debugElement.query(By.css('button[name=modificationTime]'));
    conditionButton.nativeElement.click();
    fixture.detectChanges();

    // The button should disappear after the click.
    expect(
        fixture.debugElement.queryAll(By.css('button[name=modificationTime]')))
        .toHaveSize(0);

    const minTimeInput = fixture.debugElement.query(
        By.css('input[formControlName=minLastModifiedTime'));
    minTimeInput.nativeElement.value = 42;
    minTimeInput.nativeElement.dispatchEvent(new Event('input'));

    const maxTimeInput = fixture.debugElement.query(
        By.css('input[formControlName=maxLastModifiedTime'));
    maxTimeInput.nativeElement.value = 43;
    maxTimeInput.nativeElement.dispatchEvent(new Event('input'));

    fixture.detectChanges();

    // Check that the form got updated accordingly.
    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
        (values) => {
          expect(values).toEqual({
            pathExpressions: [''],
            modificationTime: {
              minLastModifiedTime: '42',
              maxLastModifiedTime: '43',
            }
          });
          done();
        });
  });

  it('allows removing modification time expression', (done) => {
    const fixture = prepareFixture();

    const conditionButton =
        fixture.debugElement.query(By.css('button[name=modificationTime]'));
    conditionButton.nativeElement.click();
    fixture.detectChanges();

    // The button should disappear after the click.
    expect(
        fixture.debugElement.queryAll(By.css('button[name=modificationTime]')))
        .toHaveSize(0);

    // The form should now appear.
    expect(fixture.debugElement.queryAll(
               By.css('input[formControlName=minLastModifiedTime')))
        .toHaveSize(1);
    expect(fixture.debugElement.queryAll(
               By.css('input[formControlName=maxLastModifiedTime')))
        .toHaveSize(1);

    const removeButton =
        fixture.debugElement.query(By.css('.header .remove button'));
    removeButton.nativeElement.click();
    fixture.detectChanges();

    // The button should now appear.
    expect(
        fixture.debugElement.queryAll(By.css('button[name=modificationTime]')))
        .toHaveSize(1);

    // The form should now disappear.
    expect(fixture.debugElement.queryAll(
               By.css('input[formControlName=minLastModifiedTime')))
        .toHaveSize(0);
    expect(fixture.debugElement.queryAll(
               By.css('input[formControlName=maxLastModifiedTime')))
        .toHaveSize(0);

    // The form value should have no traces of the form.
    fixture.componentInstance.flowArgsForm.flowArgValues$.subscribe(
        (values) => {
          expect(values).toEqual({
            pathExpressions: [''],
          });
          done();
        });
  });
});
