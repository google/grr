/**
 * Synchronize zooming and/or selections between a set of dygraphs.
 *
 * Usage:
 *
 *   var g1 = new Dygraph(...),
 *       g2 = new Dygraph(...),
 *       ...;
 *   var sync = Dygraph.synchronize(g1, g2, ...);
 *   // charts are now synchronized
 *   sync.detach();
 *   // charts are no longer synchronized
 *
 * You can set options using the last parameter, for example:
 *
 *   var sync = Dygraph.synchronize(g1, g2, g3, {
 *      selection: true,
 *      zoom: true
 *   });
 *
 * The default is to synchronize both of these.
 *
 * Instead of passing one Dygraph objet as each parameter, you may also pass an
 * array of dygraphs:
 *
 *   var sync = Dygraph.synchronize([g1, g2, g3], {
 *      selection: false,
 *      zoom: true
 *   });
 */
(function() {
/* global Dygraph:false */
'use strict';

Dygraph.synchronize = function(/* dygraphs..., opts */) {
  if (arguments.length === 0) {
    throw 'Invalid invocation of Dygraph.synchronize(). Need >= 1 argument.';
  }

  var OPTIONS = ['selection', 'zoom'];
  var opts = {
    selection: true,
    zoom: true
  };
  var dygraphs = [];

  var prevCallbacks = {
    draw: null,
    highlight: null,
    unhighlight: null
  };

  var parseOpts = function(obj) {
    if (!(obj instanceof Object)) {
      throw 'Last argument must be either Dygraph or Object.';
    } else {
      for (var i = 0; i < OPTIONS.length; i++) {
        var optName = OPTIONS[i];
        if (obj.hasOwnProperty(optName)) opts[optName] = obj[optName];
      }
    }
  };

  if (arguments[0] instanceof Dygraph) {
    // Arguments are Dygraph objects.
    for (var i = 0; i < arguments.length; i++) {
      if (arguments[i] instanceof Dygraph) {
        dygraphs.push(arguments[i]);
      } else {
        break;
      }
    }
    if (i < arguments.length - 1) {
      throw 'Invalid invocation of Dygraph.synchronize(). ' +
            'All but the last argument must be Dygraph objects.';
    } else if (i == arguments.length - 1) {
      parseOpts(arguments[arguments.length - 1]);
    }
  } else if (arguments[0].length) {
    // Invoked w/ list of dygraphs, options
    for (var i = 0; i < arguments[0].length; i++) {
      dygraphs.push(arguments[0][i]);
    }
    if (arguments.length == 2) {
      parseOpts(arguments[1]);
    } else if (arguments.length > 2) {
      throw 'Invalid invocation of Dygraph.synchronize(). ' +
            'Expected two arguments: array and optional options argument.';
    }  // otherwise arguments.length == 1, which is fine.
  } else {
    throw 'Invalid invocation of Dygraph.synchronize(). ' +
          'First parameter must be either Dygraph or list of Dygraphs.';
  }

  if (dygraphs.length < 2) {
    throw 'Invalid invocation of Dygraph.synchronize(). ' +
          'Need two or more dygraphs to synchronize.';
  }
  
  var readycount = dygraphs.length;
  for (var i = 0; i < dygraphs.length; i++) {
    var g = dygraphs[i];
    g.ready( function() {
      if (--readycount == 0) {
        // Listen for draw, highlight, unhighlight callbacks.
        if (opts.zoom) {
          attachZoomHandlers(dygraphs, opts, prevCallbacks);
        }

        if (opts.selection) {
          attachSelectionHandlers(dygraphs, prevCallbacks);
        }
      }
    });
  }
 
  return {
    detach: function() {
      for (var i = 0; i < dygraphs.length; i++) {
        var g = dygraphs[i];
        if (opts.zoom) {
          g.updateOptions({drawCallback: prevCallbacks.draw});
        }
        if (opts.selection) {
          g.updateOptions({
            highlightCallback: prevCallbacks.highlight,
            unhighlightCallback: prevCallbacks.unhighlight
          });
        }
      }
      // release references & make subsequent calls throw.
      dygraphs = null;
      opts = null;
      prevCallbacks = null;
    }
  };
};

function attachZoomHandlers(gs, syncOpts, prevCallbacks) {
  var block = false;
  for (var i = 0; i < gs.length; i++) {
    var g = gs[i];
    prevCallbacks.draw = g.getFunctionOption('drawCallback');
    g.updateOptions({
      drawCallback: function(me, initial) {
        if (prevCallbacks.draw) prevCallbacks.draw(me, initial);
        if (block || initial) return;
        block = true;
        var range = me.xAxisRange();
        var yrange = me.yAxisRange();
        for (var j = 0; j < gs.length; j++) {
          if (gs[j] == me) continue;
          gs[j].updateOptions( {
            dateWindow: range,
            valueRange: yrange
          });
        }
        block = false;
      }
    }, false /* no need to redraw */);
  }
}

function attachSelectionHandlers(gs, prevCallbacks) {
  var block = false;
  for (var i = 0; i < gs.length; i++) {
    var g = gs[i];
    prevCallbacks.highlight = g.getFunctionOption('highlightCallback');
    prevCallbacks.unhighlight = g.getFunctionOption('unhighlightCallback');
    g.updateOptions({
      highlightCallback: function(event, x, points, row, seriesName) {
        if (prevCallbacks.highlight) {
            prevCallbacks.highlight(event, x, points, row, seriesName);
        }
        if (block) return;
        block = true;
        var me = this;
        for (var i = 0; i < gs.length; i++) {
          if (me == gs[i]) continue;
          var idx = dygraphsBinarySearch(gs[i], x);
          if (idx !== null) {
            gs[i].setSelection(idx, seriesName);
          }
        }
        block = false;
      },
      unhighlightCallback: function(event) {
        if (prevCallbacks.unhighlight) prevCallbacks.unhighlight(event);
        if (block) return;
        block = true;
        var me = this;
        for (var i = 0; i < gs.length; i++) {
          if (me == gs[i]) continue;
          gs[i].clearSelection();
        }
        block = false;
      }
    });
  }
}

// Returns the index corresponding to xVal, or null if there is none.
function dygraphsBinarySearch(g, xVal) {
  var low = 0,
      high = g.numRows() - 1;

  while (low <= high) {
    var idx = (high + low) >> 1;
    var x = g.getValue(idx, 0);
    if (x < xVal) {
      low = idx + 1;
    } else if (x > xVal) {
      high = idx - 1;
    } else {
      return idx;
    }
  }

  // TODO: give an option to find the closest point, i.e. not demand an exact match.
  return null;
}

})();
