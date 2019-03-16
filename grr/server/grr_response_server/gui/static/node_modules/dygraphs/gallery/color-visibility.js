/*global Gallery,Dygraph,data,$ */
/*jshint unused:false */
Gallery.register(
  'color-visibility',
  {
    name: "Color visibility",
    title: 'The lines should maintain their colors as their visibility is toggled.',
    setup: function(parent) {
      parent.innerHTML =
          "<div id='blah'></div>" +
          "<p><b>Display: </b>" +
          "<input type=checkbox id=0 onClick='change(this)' checked>" +
          "<label for='0'> a</label>" +
          "<input type=checkbox id=1 onClick='change(this)' checked>" +
          "<label for='1'> b</label>" +
          "<input type=checkbox id=2 onClick='change(this)' checked>" +
          "<label for='2'> c</label>" +
          "</p>";
    },
    run: function() {
      var g = new Dygraph(document.getElementById("blah"),
          "X,a,b,c\n" +
          "10,12345,23456,34567\n" +
          "11,12345,20123,31345\n",
          {
            width: 640,
            height: 480,
            colors: ['#284785', '#EE1111', '#8AE234'],
            visibility: [true, true, true]
          });
  
      $('input[type=checkbox]').click(function() {
        var el = this;
        g.setVisibility(el.id, el.checked);
      });
    }
  });
