var grr = window.grr || {};

grr.Renderer('AbstractFileTable', {
  TableSelection: function(state) {
    var unique = state.unique;
    var id = state.id;
    var renderer = state.renderer;
    var client_id = state.client_id;

    //Receive the selection event and emit a path
    grr.subscribe('select_table_' + id, function(node) {
      if (node) {
        var aff4_path = node.find('span[aff4_path]').attr('aff4_path');
        var age = node.find('span[age]').attr('age');
        grr.publish('file_select', aff4_path, age);
      }
    }, unique);

    grr.subscribe('double_click_table_' + id, function(node) {
      var is_directory = node.find('img.directory').length > 0;
      if (is_directory) {
        var aff4_path = node.find('span[aff4_path]').attr('aff4_path');
        var tree_node_id = node.find('span[tree_node_id]').attr('tree_node_id');

        grr.publish('update_file_tree', tree_node_id);
      }
    }, unique);

    // Allow the age to be updated for a basename.
    grr.subscribe('update_age', function(aff4_path, age, age_string) {
      var cell = $(unique + " span[aff4_path='" + aff4_path + "']")
          .parents('tr')
          .find('span[age]');
      cell.attr('age', age).text(age_string);
      grr.publish('file_select', aff4_path, age);
    }, unique);
  },

  TableVersionDialog: function(state) {
    var unique = state.unique;

    grr.subscribe('file_version_select', function(aff4_path) {
      var layout_state = $.extend({
        aff4_path: aff4_path
      }, grr.state);
      grr.layout('VersionSelectorDialog',
                 'version_selector_dialog_' + unique, layout_state);
      $('#version_selector_dialog_' + unique).modal('show');
    }, unique);
  },

  TreeEvent: function(state) {
    var unique = state.unique;
    var id = state.id;
    var renderer = state.renderer;
    var client_id = state.client_id;

    grr.subscribe('tree_select', function(aff4_path, selected_id,
                                          update_hash) {
      // Replace ourselves with a new table.
      grr.layout(renderer, id, {
        client_id: client_id,
        aff4_path: aff4_path
      });
      grr.state.tree_path = aff4_path;

    }, unique);

    // Allow the table content to be restored from the hash.
    $("span[aff4_path='" + grr.hash.aff4_path + "']").click();
  },

  RenderAjax: function(state) {
    var unique = state.unique;

    $('img.version-selector').unbind('click').click(function(event) {
      var aff4_path =
          $(this).parents('tr').find('span[aff4_path]').attr('aff4_path');
      grr.publish('file_version_select', aff4_path);

      event.stopPropagation();
    });
  },

  Layout: function(state) {
    grr.ExecuteRenderer('AbstractFileTable.TableSelection', state);
    grr.ExecuteRenderer('AbstractFileTable.TableVersionDialog', state);
    grr.ExecuteRenderer('AbstractFileTable.TreeEvent', state);
  }
});

grr.Renderer('FileSystemTree', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    grr.subscribe('update_file_tree', function(tree_node_id) {
      grr.openTree($('#' + unique), tree_node_id);
    }, unique);
  }
});

grr.Renderer('DownloadView', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var renderer = state.renderer;
    var aff4_path = state.aff4_path;
    var reason = state.reason;
    var file_exists = state.file_exists;
    var age_int = state.age_int;

    var button = $('#' + unique).button();
    var download_button = $('#' + unique + '_2').button();

    button.click(function(event) {
      $('#' + unique).attr('disabled', 'disabled');
      grr.layout('UpdateAttribute', unique + '_action', {
        attribute: 'aff4:content',
        aff4_type: 'VFSFile',
        aff4_path: aff4_path,
        reason: reason,
        client_id: grr.state.client_id
      });

      event.preventDefault();
    });

    // When the attribute is updated, refresh the views
    grr.subscribe('AttributeUpdated', function(path, attribute) {
      if (attribute == 'aff4:content') {
        // Update the download screen
        grr.layout(renderer, id, {
          aff4_path: path,
          reason: reason
        });
      }
    }, unique + '_action');

    if (file_exists) {
      // Attach a handler to the Download button.
      var file_state = { aff4_path: aff4_path,
                         reason: reason,
                         client_id: grr.state.client_id,
                         age: age_int };
      grr.downloadHandler(download_button, file_state, false,
                          '/render/Download/DownloadView');
    }
  }
});

grr.Renderer('UploadView', {
  Layout: function(state) {
    var unique = state.unique;
    var upload_handler = state.upload_handler;
    var upload_state = state.upload_state;

    var u_button = $('#' + unique + '_upload_button').button();
    var u_file = $('#' + unique + '_file');

    upload_state.tree_path = grr.state.tree_path;

    u_button.click(function(event) {
      grr.uploadHandler(
          upload_handler,
          unique + '_form',
          unique + '_upload_progress',
          function(dat) {
            $('#' + unique + '_upload_results').text(dat);
          },
          function(jqxhr, dat, error_val) {
            var data = jqxhr.responseText;
            data = $.parseJSON(data.substring(4, data.length));
            $('#' + unique + '_upload_results').text(data.msg);
          },
          upload_state
          );
      return false;
    });

  }
});
