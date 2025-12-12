import {MarkdownPipe} from './markdown_pipe';

describe('Markdown Pipe', () => {
  const pipe = new MarkdownPipe();

  it('shows empty string when the input is empty', () => {
    expect(pipe.transform('')).toBe('');
  });

  it('converts non-markdown text correctly', () => {
    expect(pipe.transform('Hello world')).toBe('<p>Hello world</p>\n');
  });

  it('converts bold text correctly', () => {
    expect(pipe.transform('**test**')).toBe('<p><strong>test</strong></p>\n');
  });

  it('converts italics text correctly', () => {
    expect(pipe.transform('*test*')).toBe('<p><em>test</em></p>\n');
  });

  it('converts links correctly', () => {
    expect(pipe.transform('[Google](https://google.com)')).toBe(
      '<p><a href="https://google.com">Google</a></p>\n',
    );
  });

  it('converts links in bold correctly', () => {
    expect(pipe.transform('[**Google**](https://google.com)')).toBe(
      '<p><a href="https://google.com"><strong>Google</strong></a></p>\n',
    );
  });

  it('converts line breaks to HTML paragraphs correctly', () => {
    expect(pipe.transform('Line 1\n\nLine 2')).toBe(
      '<p>Line 1</p>\n<p>Line 2</p>\n',
    );
  });
});
