import {Component, Input} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {BrowserTestingModule} from '@angular/platform-browser/testing';

import {MarkdownPipeModule} from './module';

@Component({template: `{{markdownSnippet|markdown}}`})
class TestHostComponent {
  @Input() markdownSnippet?: string;
}

describe('MarkdownPipe', () => {
  beforeEach(() => {
    TestBed
        .configureTestingModule({
          imports: [
            MarkdownPipeModule,
            BrowserTestingModule,
          ],
          declarations: [
            TestHostComponent,
          ],
        })
        .compileComponents();
  });

  it('shows empty string when the input is undefined', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.markdownSnippet = '';

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent).toBe('');
  });

  it('converts non-markdown text correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.markdownSnippet = 'Hello world';

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent.trim())
        .toBe('<p>Hello world</p>');
  });

  it('converts bold text correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.markdownSnippet = '**test**';

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent.trim())
        .toBe('<p><strong>test</strong></p>');
  });

  it('converts italics text correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.markdownSnippet = '*test*';

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent.trim())
        .toBe('<p><em>test</em></p>');
  });

  it('converts links correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.markdownSnippet = '[Google](https://google.com)';

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent.trim())
        .toBe('<p><a href="https://google.com">Google</a></p>');
  });

  it('converts links in bold correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.markdownSnippet =
        '[**Google**](https://google.com)';

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent.trim())
        .toBe(
            '<p><a href="https://google.com"><strong>Google</strong></a></p>');
  });

  it('converts line breaks to HTML paragraphs correctly', () => {
    const fixture = TestBed.createComponent(TestHostComponent);

    fixture.componentInstance.markdownSnippet = 'Line 1\n\nLine 2';

    fixture.detectChanges();

    expect(fixture.debugElement.nativeElement.textContent.trim())
        .toBe('<p>Line 1</p>\n<p>Line 2</p>');
  });
});
