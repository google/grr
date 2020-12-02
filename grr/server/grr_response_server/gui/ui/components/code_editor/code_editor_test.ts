import {TestBed, fakeAsync, tick, discardPeriodicTasks} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';

import {CodeEditorModule} from './module';
import {CodeEditor} from './code_editor';

initTestEnvironment();

describe('CodeEditor Component', () => {
  beforeEach(() => {
    return TestBed
        .configureTestingModule({
          imports: [
            CodeEditorModule,
          ],
        })
        .compileComponents();
  });

  it('initializes', fakeAsync(() => {
    const fixture = TestBed.createComponent(CodeEditor);
    // A call to fixture.detectChanges() would trigger the lifecycle hooks and
    // hence the creation of the CodeMirror editor. However, creation takes time
    // and Karma complains that there are periodic timers in the queue left.

    expect(fixture.nativeElement).toBeTruthy();
  }));
});
