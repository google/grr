import {Component} from '@angular/core';
import {TestBed, waitForAsync} from '@angular/core/testing';
import {FormControl, ReactiveFormsModule} from '@angular/forms';
import {MatFormFieldModule} from '@angular/material/form-field';
import {By} from '@angular/platform-browser';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {initTestEnvironment} from '@app/testing';
import {CodeEditor} from './code_editor';
import {CodeEditorModule} from './module';


initTestEnvironment();

/**
 * The test host component allows us to test the code editor in a
 * mat-form-field and form-control environments.
 *
 * Also, without hosting code-editor in another component it behaved weirdly:
 * the CodeMirror editor placed itself out of the code-editor DOM element.
 * I couldn't figure out why.
 */
@Component({
  template: `<mat-form-field>
        <code-editor [formControl]=query></code-editor>
      </mat-form-field>`,
})
class TestHostComponent {
  readonly query = new FormControl();
}

describe('CodeEditor Component', () => {
  beforeEach(waitForAsync(() => {
    return TestBed
        .configureTestingModule({
          imports: [
            CodeEditorModule,
            MatFormFieldModule,
            ReactiveFormsModule,
            NoopAnimationsModule,
          ],
          declarations: [
            TestHostComponent,
          ],

        })
        .compileComponents();
  }));

  function constructFixture(initialValue: string|undefined) {
    const fixture = TestBed.createComponent(TestHostComponent);
    fixture.componentInstance.query.setValue(initialValue);

    fixture.detectChanges();
    return fixture;
  }

  it('initializes', () => {
    const fixture = constructFixture('');

    const codeEditorElement = fixture.debugElement.query(By.css('code-editor'));
    expect(codeEditorElement).toBeTruthy();
  });

  it('has a code mirror component', () => {
    const fixture = constructFixture('');

    const codeMirrorElement =
        fixture.nativeElement.querySelector('.CodeMirror');
    expect(codeMirrorElement).toBeTruthy();
  });

  it('doesn\'t fail with undefined query value', () => {
    const fixture = constructFixture(undefined);

    const codeMirrorElement =
        fixture.nativeElement.querySelector('.CodeMirror');
    expect(codeMirrorElement).toBeTruthy();
  });

  it('reflects form control value in the editor', () => {
    const fixture = constructFixture('');
    fixture.componentInstance.query.setValue('Hello this is the form control.');
    fixture.detectChanges();

    const codeEditor: CodeEditor =
        fixture.debugElement.query(By.css('code-editor')).componentInstance;
    expect(codeEditor.editorValue).toBe('Hello this is the form control.');
  });

  it('reflects editor value in the form control', () => {
    const fixture = constructFixture('');

    const codeEditor: CodeEditor =
        fixture.debugElement.query(By.css('code-editor')).componentInstance;
    codeEditor.editorValue = 'Hello yes this is code editor.';
    fixture.detectChanges();

    const hostQueryFormControl = fixture.componentInstance.query;
    expect(hostQueryFormControl.value).toBe('Hello yes this is code editor.');
  });
});
