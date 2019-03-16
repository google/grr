/*global Gallery,Dygraph,data */
/*global NoisyData */
Gallery.register(
  'callbacks',
  {
    name: "Callbacks",
    title: "Hover, click and zoom to test the callbacks.",
    setup: function(parent) {
      parent.innerHTML = 
          "<div id='div_g' style='width:600px; height:300px;'></div>" +
          "<button id='clear'>Clear list<Button>" +
          "<input type='checkbox' id='highlight' checked><label for='highlight'> Show 'highlight' events</label>" +
          "<input type='checkbox' id='unhighlight' checked><label for='unhighlight'>Show 'unhighlight' events</label>" +
          "<input type='checkbox' id='showLabels' checked>" +
          "<label for='showLabels'> Show Labels on highlight</label>" +
          "<div id='status' style='width:100%; height:200px;'></div>";
    },
    run: function() {
      var g = null;
      var showLabels = document.getElementById('showLabels');
      showLabels.onclick =  function() {
        g.updateOptions({showLabelsOnHighlight: showLabels.checked});
      };

      var s = document.getElementById("status");
      var clearStatus = function() {
        s.innerHTML = '';
      };
      document.getElementById('clear').onclick = clearStatus;

      var pts_info = function(e, x, pts, row) {
        var str = "(" + x + ") ";
        for (var i = 0; i < pts.length; i++) {
          var p = pts[i];
          if (i) str += ", ";
          str += p.name + ": " + p.yval;
        }

        var x = e.offsetX;
        var y = e.offsetY;
        var dataXY = g.toDataCoords(x, y);
        str += ", (" + x + ", " + y + ")";
        str += " -> (" + dataXY[0] + ", " + dataXY[1] + ")";
        str += ", row #"+row;

        return str;
      };

      g = new Dygraph(
          document.getElementById("div_g"),
          NoisyData, {
            rollPeriod: 7,
            showRoller: true,
            errorBars: true,
  
            highlightCallback: function(e, x, pts, row) {
              if (document.getElementById('highlight').checked) {
                s.innerHTML += "<b>Highlight</b> " + pts_info(e,x,pts,row) + "<br/>";
              }
            },
  
            unhighlightCallback: function(e) {
              if (document.getElementById('unhighlight').checked) {
                s.innerHTML += "<b>Unhighlight</b><br/>";
              }
            },
  
            clickCallback: function(e, x, pts) {
              s.innerHTML += "<b>Click</b> " + pts_info(e,x,pts) + "<br/>";
            },
  
            pointClickCallback: function(e, p) {
              s.innerHTML += "<b>Point Click</b> " + p.name + ": " + p.x + "<br/>";
            },
  
            zoomCallback: function(minX, maxX, yRanges) {
              s.innerHTML += "<b>Zoom</b> [" + minX + ", " + maxX + ", [" + yRanges + "]]<br/>";
            },
  
            drawCallback: function(g) {
              s.innerHTML += "<b>Draw</b> [" + g.xAxisRange() + "]<br/>";
            }
          }
        );
    }
  });
