var grr = window.grr || {};

grr.Renderer('WizardRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    // Also show error messages on the wizard dialog since we are hiding the
    // main page.
    grr.subscribe('grr_messages', function(notification) {
      if (notification && notification.message) {
        $('#footer_message_' + unique).text(
            notification.message).show().delay(5000).fadeOut('fast');
      }
    }, 'footer_message_' + unique);


    var update_buttons = function() {
      var data = $('#Wizard_' + unique).data();

      if (data.current >= data.max_page) {
        // At the last step we hide all buttons except the finish.
        $('button.Next').hide();
        $('button.Back').hide();
        $('button.Finish').show().attr('disabled', null);
      } else {
        $('button.Next').show().attr('disabled', null);
        $('button.Finish').hide();
      }

      if (data.current > 0 && data.current < data.max_page) {
        $('button.Back').show().attr('disabled', null);
      } else {
        $('button.Back').hide();
      }
    };


    var show_page = function(old_page_number, new_page_number) {
      var wizard = $('#Wizard_' + unique);
      var old_page = wizard.find('#Page_' + old_page_number);

      old_page.hide();
      $('#Page_' + new_page_number).show().trigger('show');
      wizard.data('current', new_page_number);
    };

    var validate_transition = function(old_page_number, new_page_number) {
      var wizard_id = '#Wizard_' + unique;
      var wizard = $(wizard_id);
      var old_page = wizard.find('#Page_' + old_page_number);

      grr.update(old_page.data('renderer'), wizard_id, wizard.data(),
        function(data) {

          // Advance to the next page
          show_page(old_page_number, new_page_number);
          update_buttons();
        }, old_page_number, function(data) {

          // Error occured: publish the error and re-enable the button.
          grr.publish('grr_messages', { message: data.message });
          update_buttons();
        }, 'Validate');
    };

    $('button.Next').click(function() {
      if ($(this).attr('disabled')) return;

      var wizard = $('#Wizard_' + unique);
      var current = wizard.data('current');

      // Moving forward is only allowed if the validation succeeds.
      $(this).attr('disabled', 1);
      validate_transition(current, current + 1);
    });

    $('button.Back').click(function() {
      if ($(this).attr('disabled')) return;

      var wizard = $('#Wizard_' + unique);
      var current = wizard.data('current');

      // Moving back is always allowed.
      show_page(current, current - 1);
      update_buttons();
    });

    $('.Wizard .WizardPage').hide();
    $('#Page_0').show();

  }
});


grr.Renderer('HuntConfigureFlow', {
  Layout: function(state) {
    var id = state.id;

    grr.subscribe('flow_select', function(path) {
      var pane_id = id + '_rightPane';

      // Record the flow in the form data.
      $('#' + pane_id).closest('.FormData').data('flow_path', path);
      grr.layout('HuntFlowForm', pane_id, { flow_path: path });

    }, id);
  }
});
