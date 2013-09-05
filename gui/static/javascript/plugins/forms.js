var grr = window.grr || {};

/**
 * Namespace for forms.
 */
grr.forms = {};


/**
 * An onchange function which updates the FormData container.
 *
 * @param {Object} element an input element.
 */
grr.forms.inputOnChange = function(element) {
  var jthis = $(element);
  var json_store = jthis.closest('.FormData').data();

  json_store[jthis.attr('id')] = jthis.val();
  jthis.removeClass('unset');
};


/**
 * Change handler function for checkboxes which updates the FormData container.
 *
 * @param {Object} element an input element.
 */
grr.forms.checkboxOnChange = function(element) {
  var jthis = $(element);
  var json_store = jthis.closest('.FormData').data();

  json_store[jthis.attr('id')] = jthis.is(':checked');
  jthis.removeClass('unset');
};


/**
 * Remove all elements starting with the prefix from an input's FormData
 * container.
 *
 * @param {Object} element an input element.
 * @param {string} prefix All data members with this prefix will be cleared.
 */
grr.forms.clearPrefix = function(element, prefix) {
  var form_data = $(element).closest('.FormData');
  var data = form_data.data();

  if (form_data) {
    $.each(data, function(k, v) {
      if (k.substring(0, prefix.length) == prefix) {
        form_data.removeData(k);
      }
    });
  }
};


grr.Renderer('EmbeddedProtoFormRenderer', {
  Layout: function(state) {
    $('#' + state.unique).click(function() {
      var jthis = $(this);

      if (jthis.hasClass('ui-icon-plus')) {
        jthis.removeClass('ui-icon-plus').addClass('ui-icon-minus');

        var jcontent = $('#content_' + state.unique);

        // Load content from the server if needed.
        if (!jcontent.hasClass('Fetched')) {
          grr.update(state.renderer, 'content_' + state.unique, jthis.data());
        }

        jcontent.show();
      } else {
        // Flip the opener and remove the form.
        jthis.removeClass('ui-icon-minus').addClass('ui-icon-plus');
        $('#content_' + state.unique).hide();
      }
    });
  }
});


grr.Renderer('RepeatedFieldFormRenderer', {
  Layout: function(state) {
    $('#' + state.unique).click(function() {
      var jthis = $(this);
      var data = jthis.data();
      var content = $('#content_' + state.unique);
      var new_node = $('<div/>').data('count', data.count);

      data.count++;
      new_node.attr('id', content.attr('id') + '_' + data.count);
      content.append(new_node);
      grr.update(state.renderer, new_node.attr('id'), jthis.data());
    });
  },
  RenderAjax: function(state) {
    $('#' + state.unique).click(function() {
      $(this).parent().html('');
    });
  }
});


grr.Renderer('StringTypeFormRenderer', {
  Layout: function(state) {
    $('input#' + state.prefix).val(state.default).change();
  }
});


grr.Renderer('OptionFormRenderer', {
  Layout: function(state) {
    $('#' + state.prefix + '-option').on('change', function() {
      grr.forms.inputOnChange(this);

      var data = $.extend({}, $(this).closest('.FormData').data());
      var form = $(this).closest('.OptionList');
      data.item = form.data('item');
      data.prefix = state.prefix;

      grr.update(state.renderer, form.attr('id') + '-' + data.item, data);

      // First time the form appears, trigger the change event on the selector
      // to make the default choice appear.
    }).trigger('change');
  }
});


grr.Renderer('MultiFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var option = state.option || 'option';

    // This button is pressed when we want a new form.
    $('#AddButton' + unique).click(function() {
      var data = $(this).closest('.FormData').data();
      var count = data[option + '_count'] || 1;
      var new_id = unique + '_' + count;

      data.item = count;
      data[option + '_count'] = count + 1;

      var new_div = $('<div class="alert fade in" id="' +
          new_id + '" data-item="' + data.item + '" >');

      new_div.on('close', function() {
        var item = $(this).data('item');
        grr.forms.clearPrefix(this, option + '_' + item);
      });

      new_div.insertBefore(this);

      grr.layout(state.renderer, new_id, data);
    }).click();  // First time we show the button click it to make at least one
                 // option available.
  }
});
