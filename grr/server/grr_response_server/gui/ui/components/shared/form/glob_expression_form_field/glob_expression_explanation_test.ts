import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {Component} from '@angular/core';
import {ComponentFixture, TestBed, waitForAsync} from '@angular/core/testing';
import {MatTooltipHarness} from '@angular/material/tooltip/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {ReplaySubject, Subject} from 'rxjs';

import {GlobComponentExplanation} from '../../../../lib/models/glob_expression';
import {ExplainGlobExpressionService} from '../../../../lib/service/explain_glob_expression_service/explain_glob_expression_service';
import {initTestEnvironment} from '../../../../testing';
import {
  GlobExplanationMode,
  GlobExpressionExplanation as GlobExpressionExplanationComponent,
} from './glob_expression_explanation';

initTestEnvironment();

@Component({
  template: `
      <glob-expression-explanation clientId="C1234"
        [explanationMode]="explanationMode"
        [globExpression]="globExpression">
      </glob-expression-explanation>`,
  imports: [GlobExpressionExplanationComponent],
})
class TestHostComponent {
  explanationMode = GlobExplanationMode.ONE_EXAMPLE_VISIBLE;
  globExpression = '%%glob%%';
}

describe('Glob Expression Explanation Component', () => {
  let fixture: ComponentFixture<TestHostComponent>;
  let explainGlobExpressionService: Partial<ExplainGlobExpressionService>;
  let explanation$: Subject<readonly GlobComponentExplanation[]>;

  beforeEach(waitForAsync(() => {
    explanation$ = new ReplaySubject(1);
    explainGlobExpressionService = {
      explanation$,
      explain: jasmine.createSpy('explain'),
    };

    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, GlobExpressionExplanationComponent],
      teardown: {destroyAfterEach: false},
    })
      .overrideProvider(ExplainGlobExpressionService, {
        useFactory: () => explainGlobExpressionService,
      })
      .compileComponents();
  }));

  it('displays original glob when no explanation from service yet', async () => {
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('%%glob%%');
  });

  it('calls service with correct params', async () => {
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();
    expect(explainGlobExpressionService.explain).toHaveBeenCalledWith(
      'C1234',
      '%%glob%%',
    );
  });

  it('ONE_EXAMPLE_VISIBLE', async () => {
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.detectChanges();

    explanation$.next([
      {globExpression: '%%glob%%', examples: ['banana', 'maçã']},
    ]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('banana');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTooltipHarness);
    await harness.show();
    expect(await harness.getTooltipText()).toContain('%%glob%%');
  });

  it('ONLY_GLOB_VISIBLE', async () => {
    fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.explanationMode =
      GlobExplanationMode.ONLY_GLOB_VISIBLE;
    fixture.detectChanges();

    explanation$.next([
      {globExpression: '%%glob%%', examples: ['banana', 'maçã']},
    ]);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('%%glob%%');

    const harnessLoader = TestbedHarnessEnvironment.loader(fixture);
    const harness = await harnessLoader.getHarness(MatTooltipHarness);
    await harness.show();
    expect(await harness.getTooltipText()).toContain('banana');
  });
});
