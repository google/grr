var grr = window.grr || {};

/**
 * Namespace for artifacts.
 */
grr.artifact_view = {};


grr.Renderer('ArtifactRDFValueRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var artifact_str = state.artifact_str;

    var description_element = unique + '_artifact_description';
    var artifact_obj = JSON.parse(artifact_str);
    grr.artifact_view.renderArtifactFromObject(artifact_obj,
                                               description_element);
    // Remove heading to clean up display.
    $('div[name=artifact_name]').hide();
  }
});


grr.Renderer('ArtifactManagerToolbar', {
  Layout: function(state) {
    var unique = state.unique;

    $('#upload_dialog_' + unique).on('show.bs.modal', function() {
      grr.layout('ArtifactJsonUploadView',
                 'upload_dialog_body_' + unique);
    });

    $('#delete_confirm_dialog_' + unique).on('show.bs.modal', function() {
      grr.layout('DeleteArtifactsConfirmationDialog',
                 'delete_confirm_dialog_' + unique);
    });
  }
});


grr.Renderer('ArtifactListRenderer', {
  Layout: function(state) {
    // Populate the artifact manager.
    var selected_list_element = state.prefix;
    var artifact_list_element = state.unique + '_artifact_list';
    var os_filter_element = state.unique + '_os_filter';
    var search_element = state.unique + '_search';
    var description_element = state.unique + '_artifact_description';
    var artifact_div = $('#' + state.unique + '_artifact_renderer');

    var artifact_data = artifact_div.data();
    artifact_data.selected_list_element = selected_list_element;
    artifact_data.artifact_list_element = artifact_list_element;
    artifact_data.description_element = description_element;
    artifact_data.os_filter_element = os_filter_element;
    artifact_data.search_element = search_element;
    artifact_data.artifacts = state.artifacts;
    artifact_data.labels = state.labels;

    // Add all artifacts to list to start.
    $.each(state.artifacts, function(artifact_name, value) {
      grr.artifact_view.artifact_manager.add(artifact_div, artifact_name);
    });

    // Add all OS options to os filter.
    state.supported_os.push('All');
    $.each(state.supported_os, function(artifact_name, value) {
      grr.artifact_view.list_manager.add(os_filter_element, value);
    });
    grr.artifact_view.updateFilter(artifact_div);

    // Search Handler.
    $('#' + state.unique + '_search').keyup(function() {
      grr.artifact_view.updateFilter(artifact_div);
    });

    $('#' + os_filter_element).change(function() {
      grr.artifact_view.updateFilter(artifact_div);
    });

    // Artifact Handlers

    // Add on doubleclick.
    $('#' + artifact_list_element).dblclick(function() {
      grr.artifact_view.artifact_manager.add_selected(artifact_div,
          [this.value]);
      grr.forms.selectOnChange('#' + selected_list_element);
    });

    // Add all.
    $('#' + state.unique + '_artifact_add_all').click(function() {
      var all_opts = $('#' + artifact_list_element + ' option');
      var all_opts_vals = [];
      all_opts.each(function(index, value) {
        all_opts_vals.push(value.value);
      });
      grr.artifact_view.artifact_manager.add_selected(artifact_div,
          all_opts_vals);
      grr.forms.selectOnChange('#' + selected_list_element);
    });

    // Add.
    $('#' + state.unique + '_artifact_add').click(function() {
      var selected = $('#' + artifact_list_element).val();
      grr.artifact_view.artifact_manager.add_selected(artifact_div, selected);
      grr.forms.selectOnChange('#' + selected_list_element);
    });

    // Render Artifact information on select.

    $('#' + artifact_div.data('description_element')).hide(0);
    var select_elements = $('#' + artifact_list_element + ',#' +
        selected_list_element);
    select_elements.on('change select', function() {
      grr.artifact_view.renderArtifactFromDom(artifact_div, this.value,
          description_element);
    });

    // Select List Handlers

    // Remove on doubleclick.
    $('#' + selected_list_element).dblclick(function() {
      grr.artifact_view.artifact_manager.remove_from_selection(artifact_div,
          this.value);
    });

    // Remove.
    $('#' + state.unique + '_select_remove').click(function() {
      var selected = $('#' + selected_list_element).val();
      grr.artifact_view.artifact_manager.remove_from_selection(artifact_div,
          selected);
      grr.forms.selectOnChange('#' + selected_list_element);
    });

    // Clear.
    $('#' + state.unique + '_select_clear').click(function() {
      grr.artifact_view.artifact_manager.clear(artifact_div);
      grr.forms.selectOnChange('#' + selected_list_element);
    });
  }
});



/**
 * Update list of artifacts based on filter options.
 *
 * @param {object} artifact_div The div containing the artifact renderer.
 *
 */
grr.artifact_view.updateFilter = function(artifact_div) {
  var search_string = $('#' + artifact_div.data('search_element')).val();
  var os_filter = $('#' + artifact_div.data('os_filter_element')).val();
  grr.artifact_view.artifact_manager.filter(artifact_div, search_string,
      os_filter);
};


/**
 * Renders an artifact into an element from an initialized artifact dom.
 *
 * @param {object} artifact_div The div containing the artifact renderer.
 * @param {string} artifact_name name of artifact
 * @param {string} element to write artifact into.
 */
grr.artifact_view.renderArtifactFromDom = function(artifact_div, artifact_name,
    element) {
  artifact = artifact_div.data('artifacts')[artifact_name];
  if (! artifact) {
    return;
  }
  $('#' + artifact_div.data('description_element')).show(0);
  grr.artifact_view.renderArtifactFromObject(artifact, element);
};


/**
 * Renders an artifact into an element.
 *
 * @param {object} artifact An object containing the artifact.
 * @param {string} element to write artifact into.
 */
grr.artifact_view.renderArtifactFromObject = function(artifact, element) {
  $('#' + element + ' div[name=artifact_name]').text(artifact.name);
  $('#' + element + ' div[name=artifact_labels]').text(artifact.labels);
  var desc_element = $('#' + element + ' div[name=artifact_description]');
  // Set text from description, but allow for newlines.
  var description = desc_element.text(artifact.doc).html();
  description = description.replace(/\n/g, '<br />');
  desc_element.html(description);

  $('#' + element +
      ' div[name=artifact_conditions]').text(artifact.conditions);
  $('#' + element +
      ' div[name=artifact_dependencies]').text(artifact.dependencies);
  $('#' + element +
      ' div[name=artifact_supported_os]').text(artifact.supported_os);
  $('#' + element +
      ' div[name=artifact_output_type]').text(artifact.output_type);

  var links_element = $('#' + element + ' div[name=artifact_links]');
  links_element.html('');
  if (artifact.urls.length > 0) {
    $.each(artifact.urls, function(index, link) {
      var link_html = ('<a href="' + link + '" "noreferrer" target="_blank">' +
          link + '</a><br/>');
      links_element.append(link_html);
    });
  }

  var processor_element = '#' + element + ' table[name=artifact_processors]';
  $(processor_element + ' tr').remove();
  if (artifact.processors && artifact.processors.length > 0) {
    $.each(artifact.processors, function(index, processor) {
      processor_row = '<tr><td>Parser<td>' + processor.name + '</tr>';
      processor_row += '<tr><td>Output types<td>' + processor.output_types +
          '</tr>';
      processor_row += '<tr><td>Description<td>' + processor.doc +
          '</tr>';
      processor_row += '<tr><td></tr>';
      $(processor_element).append(processor_row);
    });
  } else {
    $(processor_element).append('<tr><td>None</td></tr>');
  }

  var source_element = '#' + element + ' table[name=artifact_sources]';
  $(source_element + ' tr').remove();
  if (artifact.sources.length > 0) {
    $.each(artifact.sources, function(index, source) {
      source_row = '<tr><td>Type<td>' + source.type +
        '</tr>';
      $.each(source.attributes, function(name, value) {
        if ($.isArray(value)) {
          value = value.join('<br>');
        }
        source_row += '<tr><td>arg:' + name + '<td>' + value + '</tr>';
      });
      source_row += '<tr><td></tr>';
      $(source_element).append(source_row);
    });
  } else {
    $(source_element).append('<tr><td>None</tr>');
  }

  $('#' + element + ' td:first-child').addClass('proto_key');
  $('#' + element + ' td:nth-child(2)').addClass('proto_value');
};


/**
 * Select List Manager object for handling a multi-select box.
 */
grr.artifact_view.list_manager = {};

/**
 * Add an element to the list.
 *
 * @param {string} domId The id of the select element to add to.
 * @param {string} value The primary value for the object.
 * @param {object} value_object Object to associate with the value.
 *
 */
grr.artifact_view.list_manager.add = function(domId, value, value_object) {
  var data = $('#' + domId).data();

  if (!(value in data)) {
    var row = '<option value="' + value + '">' + value + '</option>';
    $('#' + domId).append(row);
    data[value] = value_object;
  }
};

/**
 * Remove an element from the list.
 *
 * @param {string} domId The id of the select element to remove from.
 * @param {string} value The primary value for the object to remove.
 *
 */
grr.artifact_view.list_manager.remove = function(domId, value) {
  if (value) {
    $('#' + domId + ' option[value=' + value + ']').remove();
    $('#' + domId).removeData(value);
  }
};

/**
 * Clear the list.
 *
 * @param {string} domId The id of the select element to update to.
 *
 */
grr.artifact_view.list_manager.clear = function(domId) {
  $('#' + domId).html('');
  $('#' + domId).removeData();
};



/**
 * Artifact Manager helper object and functions.
 */
grr.artifact_view.artifact_manager = {};

/**
 * Add an element to the artifact list.
 *
 * @param {object} artifact_div The div containing the artifact renderer.
 * @param {string} artifact_name The name of the artifact.
 *
 */
grr.artifact_view.artifact_manager.add = function(artifact_div, artifact_name) {
  var artifact_list = artifact_div.data('artifact_list_element');
  grr.artifact_view.list_manager.add(artifact_list, artifact_name,
      [artifact_div.data('artifacts')[artifact_name].description]);
};

/**
 * Add artifacts to the selected list.
 *
 * @param {object} artifact_div The div containing the artifact renderer.
 * @param {string} artifact_names The names of the artifacts to add.
 *
 */
grr.artifact_view.artifact_manager.add_selected = function(artifact_div,
    artifact_names) {
  $.each(artifact_names, function(index, artifact_name) {
    var artifact = artifact_div.data('artifacts')[artifact_name];
    if (artifact) {
      grr.artifact_view.list_manager.add(
          artifact_div.data('selected_list_element'),
          artifact_name, [artifact.doc]);
    }
  });
};

/**
 * Remove artifact from the selected list.
 *
 * @param {object} artifact_div The div containing the artifact renderer.
 * @param {string} artifact_name The name of the artifact to remove.
 *
 */
grr.artifact_view.artifact_manager.remove_from_selection = function(
    artifact_div, artifact_name) {
  grr.artifact_view.list_manager.remove(
      artifact_div.data('selected_list_element'), artifact_name);
};

/**
 * Clear the selected artifact list.
 *
 * @param {object} artifact_div The div containing the artifact renderer.
 *
 */
grr.artifact_view.artifact_manager.clear = function(artifact_div) {
  grr.artifact_view.list_manager.clear(
      artifact_div.data('selected_list_element'));
};

/**
 * Filter artifact list by search string.
 *
 * @param {object} artifact_div The div containing the artifact renderer.
 * @param {string} search_string String to search artifact properties for.
 * @param {string} os The OS to limit to, if Any, do no filtering.
 *
*/
grr.artifact_view.artifact_manager.filter = function(artifact_div,
    search_string, os) {
  var artifact_list = artifact_div.data('artifact_list_element');
  grr.artifact_view.list_manager.clear(artifact_list);
  var artifact_temp = [];
  var search_string = search_string.toLowerCase();
  $.each(artifact_div.data('artifacts'),
      function(artifact_name, artifact) {
    // Filter based on supported_os.
    if ((artifact.supported_os.length == 0) ||
        ($.inArray(os, artifact.supported_os) >= 0)) {
      // Filter based on search string.
      if (artifact.doc.toLowerCase().search(search_string) != -1 ||
          artifact_name.toLowerCase().search(search_string) != -1) {
        artifact_temp.push(artifact_name);
      }
      $.each(artifact.labels, function(index, label_name) {
        if (label_name.toLowerCase().search(search_string) != -1) {
          artifact_temp.push(artifact_name);
          return false;
        }
      });
    }
  });
  // Now sort and add them.
  artifact_temp.sort();
  $.each(artifact_temp, function(index, artifact_name) {
    grr.artifact_view.artifact_manager.add(artifact_div, artifact_name);
  });

};
