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
 * Change handler function for select box which updates the FormData container.
 *
 * In this setup we want everything in the list box to be considered a value
 * not just the ones that are selected. Additionally this has be to called
 * manually, because the onchange only fires on selection, not addition to the
 * list.
 *
 * @param {Object} element an input element.
 */
grr.forms.selectOnChange = function(element) {
  var jthis = $(element);
  var json_store = jthis.closest('.FormData').data();
  var all_opts = $(element + ' option');
  var all_opts_vals = {};
  all_opts.each(function(index, value) {
    json_store[jthis.attr('id') + '-' + index] = value.value;
  });

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

  if (form_data) {
    $.each(form_data.data(), function(k, v) {
      if (k == prefix || k.substring(0, prefix.length + 1) == prefix + '-') {
        form_data.removeData(k);
      }
    });
  }
};


grr.Renderer('EmbeddedProtoFormRenderer', {
  Layout: function(state) {
    $('#' + state.unique).click(function() {
      var jthis = $(this);

      if (jthis.hasClass('glyphicon-plus')) {
        jthis.removeClass('glyphicon-plus').addClass('glyphicon-minus');

        var jcontent = $('#content_' + state.unique);

        // Load content from the server if needed.
        if (!jcontent.hasClass('Fetched')) {
          grr.update(state.renderer, 'content_' + state.unique, jthis.data());
        }

        jcontent.show();
      } else {
        // Flip the opener and remove the form.
        jthis.removeClass('glyphicon-minus').addClass('glyphicon-plus');
        $('#content_' + state.unique).hide();
      }
    });
  },

  RenderAjax: function(state) {
    // Mark the content as already fetched so we do not need to fetch again.
    $(state.id).addClass('Fetched');
  }
});


grr.Renderer('RepeatedFieldFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    $('button#add_' + unique).click(function(event) {
      var count = $(this).data('count');
      var new_id = 'content_' + unique + '_' + count;

      // Store the total count of members in the form.
      $(this).closest('.FormData').data()[state.prefix + '_count'] = count + 1;
      $(this).data('count', count + 1);

      $('#content_' + unique).append('<div id="' + new_id + '"/>');

      grr.update(state.renderer, new_id, {
        'index': count,
        'prefix': state.prefix,
        'owner': state.owner,
        'field': state.field});

      event.preventDefault();
    });
  },

  RenderAjax: function(state) {
    var unique = state.unique;

    $('button#remove_' + unique).click(function(event) {
      var form_id = '#' + unique;

      var data = $('#' + unique).data();
      grr.forms.clearPrefix(this, data.prefix + '-' + data.index);

      $(this).remove();
      $(form_id).remove();
    });
  }
});


grr.Renderer('StringTypeFormRenderer', {
  Layout: function(state) {
    var value = state.value;
    var default_value = state.default;

    if (value != null) {
      $('input#' + state.prefix).val(value).change();
    } else if (default_value != null) {
      $('input#' + state.prefix).val(default_value);
    }
  }
});

grr.Renderer('EnumFormRenderer', {
  Layout: function(state) {
    var value = state.value;
    var default_value = state.default;

    if (value != null) {
      $('select#' + state.prefix).val(value).change();
    } else if (default_value != null) {
      $('select#' + state.prefix).val(default_value);
    }
  }
});

grr.Renderer('ProtoBoolFormRenderer', {
  Layout: function(state) {
    var value = state.value;
    var default_value = state.default;

    if (value != null) {
      $('input#' + state.prefix).prop(
          'checked', value != null).val(value).change();
    } else if (default_value) {
      $('input#' + state.prefix).prop(
          'checked', default_value).val(default_value);
    }
  }
});


grr.Renderer('OptionFormRenderer', {
  Layout: function(state) {
    var optionControl = $('#' + state.prefix + '-option');
    optionControl.on('change', function() {
      grr.forms.inputOnChange(this);

      var data = $.extend({}, $(this).closest('.FormData').data());
      data['prefix'] = state.prefix;
      grr.update(state.renderer, state.unique + '-option-form', data);

      // First time the form appears, trigger the change event on the selector
      // to make the default choice appear.
    });

    if (state.default_item_type) {
      optionControl.val(state.default_item_type);
    }
    optionControl.trigger('change');
  }
});


grr.Renderer('MultiFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var option = state.option || 'option';

    // This button is pressed when we want a new form.
    var addButton = $('#AddButton' + unique);
    addButton.bind('addItem', function(event, defaultItemType) {
      var data = $(this).closest('.FormData').data();
      var count = data[option + '_count'] || 1;
      var new_id = unique + '_' + count;

      data.item = count;
      data['default_item_type'] = defaultItemType;
      data[option + '_count'] = count + 1;

      var new_div = $('<div class="alert fade in" id="' +
          new_id + '" data-item="' + count + '" >');

      new_div.insertBefore(this);

      grr.layout(state.renderer, new_id, data);
    });
    addButton.click(function() {
      addButton.trigger('addItem');
    });

    if (state.add_one_default) {
      // If "add_one_default" argument is true, first time we show the button
      // click it to make at least one option available.
      addButton.click();
    }
  },

  LayoutItem: function(state) {
    var unique = state.unique;
    var option = state.option || 'option';

    // This button is pressed when current form is removed.
    var removeButton = $('#RemoveButton' + unique);
    removeButton.click(function() {
      var item = $(this).parent().data('item');
      grr.forms.clearPrefix(this, option + '_' + item);
    });
  }
});


grr.Renderer('SemanticProtoFormRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    $('#advanced_label_' + unique).click(function() {
      var advancedControls = $('#advanced_controls_' + unique);
      if (advancedControls.hasClass('hide')) {
        advancedControls.removeClass('hide');
      } else {
        advancedControls.addClass('hide');
      }

      var icon = $('#' + unique + ' .advanced-icon:last');
      if ($('#advanced_controls_' + unique).is(':visible')) {
        icon.removeClass('glyphicon-chevron-right').addClass(
            'glyphicon-chevron-down');
      } else {
        icon.removeClass('glyphicon-chevron-down').addClass(
            'glyphicon-chevron-right');
      }
    });

    $('#' + unique + ' i.advanced-icon').click(function() {
      $('#advanced_label_' + unique).trigger('click');
    });
  }
});


grr.Renderer('RDFDatetimeFormRenderer', {
  Layout: function(state) {
    $('#' + state.prefix + '_picker').datepicker({
      showAnim: '',
      changeMonth: true,
      changeYear: true,
      showOn: 'button',
      buttonImage: 'static/images/clock.png',
      buttonImageOnly: true,
      altField: '#' + state.prefix,
      onSelect: function(dateText, inst) {
        $('#' + state.prefix).trigger('change');
     }
    });
  }
});


grr.Renderer('MultiSelectListRenderer', {
  Layout: function(state) {
    var prefix = state.prefix;

    // Height hack as CSS isn't handled properly for multiselect.
    var multiselect_height = parseInt($('#' + prefix + ' option').length) * 15;
    $('#' + prefix).css('height', multiselect_height);
  }
});
