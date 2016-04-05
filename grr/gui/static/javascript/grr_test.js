/* Copyright 2011 Google Inc. All Rights Reserved.
 */

/**
 * @fileoverview Tests for GRR frontend.
 */

/**
 * Make sure that the jQuery ajax handler refuses to work if the server does not
 * use XSSI protections.
 */
function testXSSIprotection() {
  grr.init();

  // This should be ok
  var result = jQuery.parseJSON(')]}\n[]');

  assertEquals(result.length, 0);

  // This should fail
  try {
    jQuery.parseJSON('hello');
  } catch (e) {
    return;
  }
  fail('No Exception thrown by parseJSON');
}


/**
 * Check that publish/subscribe mechanism works. We publish one event and check
 * that two subscribers are notified.
 */
function testSubscribePublish() {
  grr.init();

  var success = false;
  var success2 = false;

  return;
  // Make a div to hang the callbacks on
  $('#test').append('<div id="testSubscribePublish">Hello</div>');

  // Subscribe to the event
  grr.subscribe('testqueue_sp', function(value, event, data) {
    assertEquals(value, 'value');
    assertEquals(event, 'event');
    assertEquals(data, 'data');
    success = true;
  }, 'testSubscribePublish');

  // Subscribe again to the event
  grr.subscribe('testqueue_sp', function(value, event, data) {
    assertEquals(value, 'value');
    assertEquals(event, 'event');
    assertEquals(data, 'data');
    success2 = true;
  }, 'testSubscribePublish');

  // Now publish the event
  grr.publish('testqueue_sp', 'value', 'event', 'data');
  assertTrue(success);
  assertTrue(success2);

  // Remove the node from the DOM
  $('#test').html('');
  success = false;

  // Test that now events do not fire
  grr.publish('testqueue_sp', 'value', 'event', 'data');
  assertFalse(success);
}

/**
 * Check that the grr.layout function updates a dom element from a renderer.
 */
function testLayout() {
  var renderer = 'TestRenderer';
  var domId = 'test';
  var state = {id: domId};

  // Mock out the ajax call
  $.ajax = function(options) {
    assertEquals(options.url, 'render/Layout/TestRenderer');
    assertEquals(options.data.id, domId);
    // Just call the success callback directly:
    options.success('foobar');
  };

  // Make the call
  grr.layout(renderer, domId, state);

  // Check that the dom was updated
  var node = $('#test');

  assertEquals(node.html(), 'foobar');
}

/**
 * Check that the tree widget refreshes from a renderer and publishes selection
 * events.
 */
function testTree() {
  var state = {};
  var renderer = 'TestRenderer';
  var domId = 'test';

  var tree_created = false;
  var select_handler = false;
  var path_selected = false;

  grr.init();

  grr.bind_dict = {};

  // Mock jstree
  $.fn.jstree = function(opts) {
    assertEquals(opts.json_data.ajax.url,
      'render/RenderAjax/TestRenderer');

    tree_created = true;
  };

  // Check that the select event was bound. Save the handler so we can call it
  // directly later.
  $.fn.bind = function(event, handler) {
    grr.bind_dict[event] = handler;
  };

  // Set up a subscriber for tree selection
  grr.subscribe('testqueue_t', function(value, event, data) {
    assertEquals(value, '/test/test');
    path_selected = true;
  }, 'body');

  // Make the tree
  grr.grrTree(renderer, domId, 'testqueue_t', state);

  // data emulates a dom element. NOTE- we rely on the server to set a path
  // attribute for each element - can we do this automatically in javascript?
  var data = {};
  data.args = {};
  data.inst = {};
  data.inst.get_path = function(obj) {
    return ['test', 'test'];
  };
  data.rslt = {};

  // Mock a select event
  grr.bind_dict['select_node.jstree']('event', data);

  // Check that the tree was created and selection worked.
  assertTrue(tree_created);
  assertTrue(path_selected);
}


/**
 * Check that previously set timers are cleared.
 */
function testDelayedSubscribe() {
  var timer_ids = {};
  var _setTimeout = window.setTimeout;
  var _clearTimeout = window.clearTimeout;
  var timer_cleared = false;
  var time_delay = 500;
  var subscribe_called = false;

  grr.init();

  // We subscribe this function
  grr.delayedSubscribe('testqueue_ds', time_delay, 'unique_id',
    function(value, event, data) {
      assertEquals(value, 'value');
      assertEquals(event, 'event');
      assertEquals(data, 'data');
      subscribe_called = true;
  });

  // Below we simulate an event, then a short time later another event (before
  // the delay). The first event should be cleared and the second should fire.
  window.setTimeout = function(handle, delay) {
    return 'First';
  };

  // This should not be called first time
  window.clearTimeout = null;

  // First event published - should schedule the first timer
  grr.publish('testqueue_ds', 'value', 'event', 'data');

  // Handler should not be called yet
  assertFalse(subscribe_called);

  // Second event published should clear the first timer, set a second timer,
  // and directly call it.
  window.setTimeout = function(timer, delay) {
    assertEquals(delay, time_delay * 1000);

    // Just call the handler right away
    if (timer) {
      timer();
    }

    return 'Second';
  };

  window.clearTimeout = function(timer) {
    assertEquals(timer, 'First');
    timer_cleared = true;
  };

  grr.publish('testqueue_ds', 'value', 'event', 'data');

  // Check everything
  assertTrue(timer_cleared);
  assertTrue(subscribe_called);

  // Restore the mocks
  window.setTimeout = _setTimeout;
  window.clearTimeout = _clearTimeout;
}
