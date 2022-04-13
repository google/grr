import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {ReactiveFormsModule, UntypedFormControl} from '@angular/forms';
import {MatAutocompleteHarness} from '@angular/material/autocomplete/testing';
import {MatInputHarness} from '@angular/material/input/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ReplaySubject, Subject} from 'rxjs';

import {GlobComponentExplanation} from '../../../lib/api/api_interfaces';
import {Client} from '../../../lib/models/client';
import {newClient} from '../../../lib/models/model_test_util';
import {ExplainGlobExpressionService} from '../../../lib/service/explain_glob_expression_service/explain_glob_expression_service';
import {STORE_PROVIDERS} from '../../../store/store_test_providers';
import {initTestEnvironment} from '../../../testing';

import {GlobExpressionExplanationModule} from './module';

initTestEnvironment();

@Component({
  template: `
      <app-glob-expression-input [formControl]="formControl" [client]="client">
      </app-glob-expression-input>`,
})
class TestHostComponent {
  client: Client|null = null;
  readonly formControl = new UntypedFormControl('');
}

describe('app-glob-expression-input', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let explainGlobExpressionService: Partial<ExplainGlobExpressionService>;
  let explanation$: Subject<ReadonlyArray<GlobComponentExplanation>>;

  beforeEach(waitForAsync(() => {
    explanation$ = new ReplaySubject(1);
    explainGlobExpressionService = {
      explanation$,
      explain: jasmine.createSpy('explain'),
    };

    TestBed
        .configureTestingModule({
          imports: [
            NoopAnimationsModule,
            GlobExpressionExplanationModule,
            ReactiveFormsModule,
          ],
          declarations: [
            TestHostComponent,
          ],
          providers: [
            ...STORE_PROVIDERS,
          ],
          teardown: {destroyAfterEach: false}
        })
        .overrideProvider(
            ExplainGlobExpressionService,
            {useFactory: () => explainGlobExpressionService})
        .compileComponents();

    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
  }));

  it('writes FormControl value to the input field', async () => {
    fixture.componentInstance.formControl.setValue('/foo');
    fixture.detectChanges();

    const loader = TestbedHarnessEnvironment.loader(fixture);
    const inputHarness = await loader.getHarness(MatInputHarness);
    expect(await inputHarness.getValue()).toEqual('/foo');
  });

  it('emits the input field value as FormControl value', async () => {
    const loader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await loader.getHarness(MatAutocompleteHarness);
    await harness.enterText('/foo');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Resolves to: /foo');
    expect(fixture.componentInstance.formControl.value).toEqual('/foo');
  });

  it('shows autocomplete for KnowledgeBase entries when typing %%',
     async () => {
       fixture.componentInstance.client = newClient({
         knowledgeBase: {
           fqdn: 'foo.bar',
           osMajorVersion: 10,
           users: [{username: 'testuser'}]
         }
       });
       fixture.detectChanges();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const harness = await loader.getHarness(MatAutocompleteHarness);

       await harness.enterText('/prefix/%');
       expect(await harness.isOpen()).toBeFalse();

       await harness.enterText('/prefix/%%');
       const options = await harness.getOptions();
       expect(options.length).toEqual(3);

       expect(await options[0].getText()).toContain('%%fqdn%%');
       expect(await options[0].getText()).toContain('foo.bar');
       expect(await options[1].getText()).toContain('%%os_major_version%%');
       expect(await options[1].getText()).toContain('10');
       expect(await options[2].getText()).toContain('%%users.username%%');
       expect(await options[2].getText()).toContain('testuser');
     });

  it('inserts selected autocomplete option, retaining prefix text',
     async () => {
       fixture.componentInstance.client = newClient({
         knowledgeBase: {
           fqdn: 'foo.bar',
           osMajorVersion: 10,
           users: [{username: 'testuser'}]
         }
       });
       fixture.detectChanges();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const harness = await loader.getHarness(MatAutocompleteHarness);

       await harness.enterText('/prefix/%%');

       const options = await harness.getOptions();
       expect(options.length).toEqual(3);
       expect(await options[2].getText()).toContain('%%users.username%%');
       await options[2].click();
       fixture.detectChanges();

       expect(fixture.componentInstance.formControl.value)
           .toEqual('/prefix/%%users.username%%');
     });

  it('inserts selected autocomplete option, retaining prefix text',
     async () => {
       fixture.componentInstance.client = newClient({
         knowledgeBase: {
           fqdn: 'foo.bar',
           osMajorVersion: 10,
           users: [{username: 'testuser'}]
         }
       });
       fixture.detectChanges();

       const loader = TestbedHarnessEnvironment.loader(fixture);
       const harness = await loader.getHarness(MatAutocompleteHarness);

       await harness.enterText('/prefix/%%');

       const options = await harness.getOptions();
       expect(options.length).toEqual(3);
       expect(await options[2].getText()).toContain('%%users.username%%');
       await options[2].click();
       fixture.detectChanges();

       expect(fixture.componentInstance.formControl.value)
           .toEqual('/prefix/%%users.username%%');
     });
});
