/*global Gallery,Dygraph,data */
Gallery.register(
  'color-cycle',
  {
    name: "Color cycle",
    title: 'Different color cycles',
    setup: function(parent) {
      parent.innerHTML =
          "<div id='blah'></div>" +
          "<p><b>Colors: </b>" +
          "<button id='0'> first set</button>" +
          "<button id='1'> second set</button>" +
          "<button id='2'> undefined</button>" +
          "</p>";
    },
    run: function() {
      var colorSets = [
        ['#284785', '#EE1111', '#8AE234'],
        ['#444444', '#888888', '#DDDDDD'],
        null
      ];
      var chart = new Dygraph(document.getElementById("blah"),
                          "X,a,b,c\n" +
                          "10,12345,23456,34567\n" +
                          "11,12345,20123,31345\n",
                          {
                            width: 640,
                            height: 480,
                            colors: colorSets[0]
                          });
  
      function change(event) {
        chart.updateOptions({colors: colorSets[event.target.id]});
      }
      document.getElementById("0").onclick = change;
      document.getElementById("1").onclick = change;
      document.getElementById("2").onclick = change;
    }
  });
