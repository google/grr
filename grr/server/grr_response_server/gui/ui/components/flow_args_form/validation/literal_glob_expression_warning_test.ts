import {TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {initTestEnvironment} from '../../../testing';

import {LiteralGlobExpressionWarning} from './literal_glob_expression_warning';
import {ValidationModule} from './validation_module';

initTestEnvironment();

describe('app-literal-glob-expression-warning', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [ValidationModule, NoopAnimationsModule],
      providers: [],
      teardown: {destroyAfterEach: false},
    }).compileComponents();
  }));

  it('is created successfully', () => {
    const fixture = TestBed.createComponent(LiteralGlobExpressionWarning);
    const componentInstance = fixture.componentInstance;
    expect(componentInstance).toBeTruthy();
  });

  it('is hidden when path does not contain *', () => {
    const fixture = TestBed.createComponent(LiteralGlobExpressionWarning);
    fixture.detectChanges();

    fixture.componentInstance.path = '/foo';
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toEqual('');
  });

  it('shows a warning when path contains *', () => {
    const fixture = TestBed.createComponent(LiteralGlobExpressionWarning);
    fixture.detectChanges();

    fixture.componentInstance.path = '/foo*';
    fixture.detectChanges();

    expect(fixture.nativeElement.innerText).toContain(
      'path uses */** literally',
    );
  });
});
