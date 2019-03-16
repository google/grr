/*global Gallery,Dygraph,data */
/*global NoisyData,downV3,moveV3,upV3,clickV3,dblClickV3,scrollV3,restorePositioning,downV4,moveV4,upV4,dblClickV4,captureCanvas */

Gallery.register(
  'interaction',
  {
    name: 'Custom interaction models',
    title: 'title',
    setup: function(parent) {
      parent.innerHTML = [
          "<h3>Default interaction model</h3>",
          "<div style='width:600px;'>",
          "  <p style='text-align:center;'>",
          "    Zoom: click-drag, Pan: shift-click-drag, Restore: double-click",
          "  </p>",
          "  <div id='div_g' style='width:600px; height:300px;'></div>",
          "</div>",
          "",
          "<h3>Empty interaction model</h3>",
          "<div style='width:600px;'>",
          "  <p style='text-align:center;'>",
          "    Click and drag all you like, it won't do anything!",
          "  </p>",
          "  <div id='div_g2' style='width:600px; height:300px;'></div>",
          "</div>",
          "<div id='g2_console'></div>", // what is this?
          "",
          "<h3>Custom interaction model</h3>",
          "<div style='width:600px;'>",
          "  <p style='text-align:center;'>",
          "    Zoom in: double-click, scroll wheel<br/>",
          "    Zoom out: ctrl-double-click, scroll wheel<br/>",
          "    Standard Zoom: shift-click-drag",
          "    Standard Pan: click-drag<br/>",
          "    Restore zoom level: press button<br/>",
          "  </p>",
          "  <button id='restore3'>Restore position</button>",
          "  <div id='div_g3' style='width:600px; height:300px;'></div>",
          "</div>",
          "<h3>Fun model!</h3>",
          "<div style='width:600px;'>",
          "  <p style='text-align:center;'>",
          "    Keep the mouse button pressed, and hover over all points",
          "    to mark them.",
          "  </p>",
          "  <div id='div_g4' style='width:600px; height:300px;'></div>",
          "</div>"
          ].join('\n');

    },
    run: function() {
      var lastClickedGraph;
      // TODO(konigsberg): Add cleanup to remove callbacks.
      Dygraph.addEvent(document, "mousewheel", function() { lastClickedGraph = null; });
      Dygraph.addEvent(document, "click", function() { lastClickedGraph = null; });
      new Dygraph(document.getElementById("div_g"),
           NoisyData, { errorBars : true });
      new Dygraph(document.getElementById("div_g2"),
           NoisyData,
           {
             errorBars : true,
             interactionModel: {}
           });
      var g3 = new Dygraph(document.getElementById("div_g3"),
           NoisyData, { errorBars : true, interactionModel : {
            'mousedown' : downV3,
            'mousemove' : moveV3,
            'mouseup' : upV3,
            'click' : clickV3,
            'dblclick' : dblClickV3,
            'mousewheel' : scrollV3
      }});
      document.getElementById("restore3").onclick = function() {
        restorePositioning(g3);
      };
      new Dygraph(document.getElementById("div_g4"),
           NoisyData, {
             errorBars : true,
             drawPoints : true,
             interactionModel : {
               'mousedown' : downV4,
               'mousemove' : moveV4,
               'mouseup' : upV4,
               'dblclick' : dblClickV4
             },
             underlayCallback : captureCanvas
          });
    }
  });
