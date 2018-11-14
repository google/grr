goog.module('grrUi.forms.globExpressionFormDirectiveTest');
goog.setTestOnly();

const {getSuggestions} = goog.require('grrUi.forms.globExpressionFormDirective');

describe('grr-glob-expression-form directive', () => {
  it('shows no autocomplete without delimiter', () => {
    expect(getSuggestions('fooba', ['foobar', 'baz'])).toEqual([]);
  });

  it('shows no autocompletion with closed delimiter', () => {
    expect(getSuggestions('%%foobar%%/foobar', ['foobar', 'baz'])).toEqual([]);
  });

  it('shows no autocompletion for closed group', () => {
    expect(getSuggestions('%%foobar%%foo', ['foobar', 'baz'])).toEqual([]);
  });

  it('shows autocompletion for matching prefix', () => {
    expect(getSuggestions('%%fooba', ['foobar', 'baz'])).toEqual([
      {suggestion: '%%foobar%%', expressionWithSuggestion: '%%foobar%%'}
    ]);
  });

  it('shows autocompletion for partial matching', () => {
    expect(getSuggestions('%%oba', ['foobar', 'baz'])).toEqual([
      {suggestion: '%%foobar%%', expressionWithSuggestion: '%%foobar%%'}
    ]);
  });

  it('shows autocompletion while closing term', () => {
    expect(getSuggestions('%%foobar%', ['foobar', 'baz'])).toEqual([
      {suggestion: '%%foobar%%', expressionWithSuggestion: '%%foobar%%'}
    ]);
  });

  it('shows autocompletion with unrelated query prefix', () => {
    expect(getSuggestions('/bar/%%foo', ['foobar', 'baz'])).toEqual([
      {suggestion: '%%foobar%%', expressionWithSuggestion: '/bar/%%foobar%%'}
    ]);
  });

  it('hides autocompletion for closed term', () => {
    expect(getSuggestions('%%foo%%', ['foobar', 'foo'])).toEqual([]);
  });

  it('shows multiple autocomplete suggestions', () => {
    const sug = getSuggestions('%%ba', ['foobar', 'baz']);
    expect(sug.length).toBe(2);
    expect(sug).toContain(
        {suggestion: '%%foobar%%', expressionWithSuggestion: '%%foobar%%'});
    expect(sug).toContain(
        {suggestion: '%%baz%%', expressionWithSuggestion: '%%baz%%'});
  });
});


exports = {};
