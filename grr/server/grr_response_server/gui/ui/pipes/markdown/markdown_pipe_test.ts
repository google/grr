import {MarkdownPipe} from './markdown_pipe';

describe('Markdown Pipe', () => {
  const pipe = new MarkdownPipe();

  it('shows empty string when the input is empty', () => {
    expect(pipe.transform('')).toBe('');
  });

  it('converts non-markdown text correctly', () => {
    expect(normalize(pipe.transform('Hello world'))).toBe(
      normalize('<p>Hello world</p>\n'),
    );
  });

  it('converts bold text correctly', () => {
    expect(normalize(pipe.transform('**test**'))).toBe(
      normalize('<p><strong>test</strong></p>\n'),
    );
  });

  it('converts italics text correctly', () => {
    expect(normalize(pipe.transform('*test*'))).toBe(
      normalize('<p><em>test</em></p>\n'),
    );
  });

  it('converts links correctly', () => {
    expect(normalize(pipe.transform('[Google](https://google.com)'))).toBe(
      normalize('<p><a href="https://google.com">Google</a></p>\n'),
    );
  });

  it('converts links in bold correctly', () => {
    expect(normalize(pipe.transform('[**Google**](https://google.com)'))).toBe(
      normalize(
        '<p><a href="https://google.com"><strong>Google</strong></a></p>\n',
      ),
    );
  });

  it('converts line breaks to HTML paragraphs correctly', () => {
    expect(normalize(pipe.transform('Line 1\n\nLine 2'))).toBe(
      normalize('<p>Line 1</p>\n<p>Line 2</p>\n'),
    );
  });
});

/**
 * Removes all whitespaces from a given HTML string. This is useful for
 * comparing HTML strings in tests in a lenient way.
 */
function normalize(html: string | undefined): string | undefined {
  return html?.replace(/\s/g, '');
}
