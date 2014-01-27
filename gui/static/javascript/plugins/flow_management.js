var grr = window.grr || {};

/**
 * Namespace for the glob completer.
 */
grr.glob_completer = {};

/**
 * A filter function which matches the start of the completion list.
 *
 * @param {Array} completions the completion list
 * @param {string} term is the term to match.
 *
 * @return {Array} a list of matches.
 */
grr.glob_completer.filter = function(completions, term) {
  var matcher = new RegExp('^' + $.ui.autocomplete.escapeRegex(term), 'i');
  return $.grep(completions, function(value) {
    return matcher.test(value.label || value.value || value);
  });
};

/**
 * Build a completer on top of a text input.
 *
 * @param {string} dom_id is the DOM id of the text input field.
 * @param {Array} completions are possible completions for %% sequences.
 */
grr.glob_completer.Completer = function(dom_id, completions) {
  $('#' + dom_id).bind('keydown', function(event) {
    if (event.keyCode === $.ui.keyCode.TAB &&
        $(this).data('ui-autocomplete').menu.active) {
      event.preventDefault();
    }
  }).autocomplete({
    minLength: 0,
    source: function(request, response) {
      var terms = request.term.split(/%%/);
      if (terms.length % 2) {
        response([]);
      } else {
        response(grr.glob_completer.filter(completions, terms.pop()));
      }
    },
    focus: function() {
      // prevent value inserted on focus
      return false;
    },
    select: function(event, ui) {
      var terms = this.value.split(/%%/);

      // remove the current input
      terms.pop();

      // add the selected item
      terms.push(ui.item.value);
      terms.push('');

      this.value = terms.join('%%');
      return false;
    }
  }).wrap('<abbr title="Type %% to open a list of possible completions."/>');
};

grr.Renderer('GlobExpressionFormRenderer', {
  Layout: function(state) {
    grr.glob_completer.Completer(state.prefix, state.completions);
  }
});
