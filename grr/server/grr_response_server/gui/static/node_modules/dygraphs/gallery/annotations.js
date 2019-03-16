/*global Gallery,Dygraph,data */
Gallery.register(
  'annotations',
  {
    name: 'Annotations', 
    title: 'Dynamic Annotations Demo',
    setup: function(parent) {
      parent.innerHTML = [
          "<p>Click any point to add an annotation to it or click 'Add Annotation'.</p>",
          "<button id='add'>Add Annotation></button>",
          "<button id='bottom'>Shove to bottom</button>",
          "<div id='list'></div>",
          "<div id='g_div'></div>",
          "<div id='events'></div>" ].join("\n");
     },

    run: function() {
      var eventDiv = document.getElementById("events");
      function nameAnnotation(ann) {
        return "(" + ann.series + ", " + ann.x + ")";
      }
  
      var g = new Dygraph(
              document.getElementById("g_div"),
              function() {
                var zp = function(x) { if (x < 10) return "0"+x; else return x; };
                var r = "date,parabola,line,another line,sine wave\n";
                for (var i=1; i<=31; i++) {
                  r += "200610" + zp(i);
                  r += "," + 10*(i*(31-i));
                  r += "," + 10*(8*i);
                  r += "," + 10*(250 - 8*i);
                  r += "," + 10*(125 + 125 * Math.sin(0.3*i));
                  r += "\n";
                }
                return r;
              },
              {
                rollPeriod: 1,
                showRoller: true,
                width: 480,
                height: 320,
                drawCallback: function(g) {
                  var ann = g.annotations();
                  var html = "";
                  for (var i = 0; i < ann.length; i++) {
                    var name = nameAnnotation(ann[i]);
                    html += "<span id='" + name + "'>";
                    html += name + ": " + (ann[i].shortText || '(icon)');
                    html += " -> " + ann[i].text + "</span><br/>";
                  }
                  document.getElementById("list").innerHTML = html;
                }
              }
          );

      var last_ann = 0;
      var annotations = [];
      for (var x = 10; x < 15; x += 2) {
        annotations.push( {
          series: 'sine wave',
          x: "200610" + x,
          shortText: x,
          text: 'Stock Market Crash ' + x
        } );
        last_ann = x;
      }
      annotations.push( {
        series: 'another line',
        x: "20061013",
        icon: 'images/dollar.png',
        width: 18,
        height: 23,
        tickHeight: 4,
        text: 'Another one',
        cssClass: 'annotation',
        clickHandler: function() {
          eventDiv.innerHTML += "special handler<br/>";
        }
      } );
      g.setAnnotations(annotations);

      document.getElementById('add').onclick = function() {
        var x = last_ann + 2;
        annotations.push( {
          series: 'line',
          x: "200610" + x,
          shortText: x,
          text: 'Line ' + x,
          tickHeight: 10
        } );
        last_ann = x;
        g.setAnnotations(annotations);
      };

      var bottom = document.getElementById('bottom');

      bottom.onclick = function() {
        var to_bottom = bottom.textContent == 'Shove to bottom';

        var anns = g.annotations();
        for (var i = 0; i < anns.length; i++) {
          anns[i].attachAtBottom = to_bottom;
        }
        g.setAnnotations(anns);

        if (to_bottom) {
          bottom.textContent = 'Lift back up';
        } else {
          bottom.textContent = 'Shove to bottom';
        }
      };

      var saveBg = '';
      var num = 0;
      g.updateOptions( {
        annotationClickHandler: function(ann, point, dg, event) {
          eventDiv.innerHTML += "click: " + nameAnnotation(ann) + "<br/>";
        },
        annotationDblClickHandler: function(ann, point, dg, event) {
          eventDiv.innerHTML += "dblclick: " + nameAnnotation(ann) + "<br/>";
        },
        annotationMouseOverHandler: function(ann, point, dg, event) {
          document.getElementById(nameAnnotation(ann)).style.fontWeight = 'bold';
          saveBg = ann.div.style.backgroundColor;
          ann.div.style.backgroundColor = '#ddd';
        },
        annotationMouseOutHandler: function(ann, point, dg, event) {
          document.getElementById(nameAnnotation(ann)).style.fontWeight = 'normal';
          ann.div.style.backgroundColor = saveBg;
        },
    
        pointClickCallback: function(event, p) {
          // Check if the point is already annotated.
          if (p.annotation) return;
    
          // If not, add one.
          var ann = {
            series: p.name,
            xval: p.xval,
            shortText: num,
            text: "Annotation #" + num
          };
          var anns = g.annotations();
          anns.push(ann);
          g.setAnnotations(anns);
    
          num++;
        }
      });
    }
  });
