
module("event");

test( "live with non-null,defined data", function() {
	expect( 3 );

	var handler = function( event, data ) {
			equal( data, 0, "non-null, defined data (zero) is correctly passed" );
		};

	expectWarning( "live", function() {
		jQuery("#foo").live("foo", handler);
		jQuery("#foo").trigger("foo", 0);
	});
	expectWarning( "die", function() {
		jQuery("#foo").die("foo", handler);
	});
});

test( "live/die(Object)", function() {
	expect( 4 );

	var clickCounter = 0,
		mouseoverCounter = 0,
		$p = jQuery("#firstp"),
		$a = $p.find("a:first"),
		events = {
			"click": function( event ) {
				clickCounter += ( event.data || 1 );
			},
			"mouseover": function( event ) {
				mouseoverCounter += ( event.data || 1 );
			}
		},
		trigger = function() {
			$a.trigger("click").trigger("mouseover");
		};

	$a.live( events );

	trigger();
	trigger();
	equal( clickCounter, 2, "live click" );
	equal( mouseoverCounter, 2, "live mouseover" );

	$a.die( events );

	trigger();
	equal( clickCounter, 2, "click after die" );
	equal( mouseoverCounter, 2, "mouseover after die" );
});

test( "live immediate propagation", function() {
	expect( 1 );

	var lastClick,
		$p = jQuery("#firstp"),
		$a = $p.find("a:first");

	lastClick = "";
	$a.live( "click", function(e) {
		lastClick = "click1";
		e.stopImmediatePropagation();
	});
	$a.live( "click", function(e) {
		lastClick = "click2";
	});
	$a.trigger( "click" );
	equal( lastClick, "click1", "live stopImmediatePropagation" );
	$a.die( "click" );
});

test( "live(name, false), die(name, false)", function() {
	expect(3);

	var main = 0;
	jQuery("#qunit-fixture").live("click", function(e){ main++; });
	jQuery("#ap").trigger("click");
	equal( main, 1, "Verify that the trigger happened correctly." );

	main = 0;
	jQuery("#ap").live("click", false);
	jQuery("#ap").trigger("click");
	equal( main, 0, "Verify that no bubble happened." );

	main = 0;
	jQuery("#ap").die("click", false);
	jQuery("#ap").trigger("click");
	equal( main, 1, "Verify that the trigger happened correctly." );
	jQuery("#qunit-fixture").die("click");
});

test( ".live()/.die()", function() {
	expect(66);

	var submit = 0, div = 0, livea = 0, liveb = 0,
		livec, lived, livee, elemDiv,
		hash, event, clicked, container, called;

	jQuery("div").live("submit", function(){ submit++; return false; });
	jQuery("div").live("click", function(){ div++; });
	jQuery("div#nothiddendiv").live("click", function(){ livea++; });
	jQuery("div#nothiddendivchild").live("click", function(){ liveb++; });

	// Nothing should trigger on the body
	jQuery("body").trigger("click");
	equal( submit, 0, "Click on body" );
	equal( div, 0, "Click on body" );
	equal( livea, 0, "Click on body" );
	equal( liveb, 0, "Click on body" );

	// This should trigger two events
	submit = 0; div = 0; livea = 0; liveb = 0;
	jQuery("div#nothiddendiv").trigger("click");
	equal( submit, 0, "Click on div" );
	equal( div, 1, "Click on div" );
	equal( livea, 1, "Click on div" );
	equal( liveb, 0, "Click on div" );

	// This should trigger three events (w/ bubbling)
	submit = 0; div = 0; livea = 0; liveb = 0;
	jQuery("div#nothiddendivchild").trigger("click");
	equal( submit, 0, "Click on inner div" );
	equal( div, 2, "Click on inner div" );
	equal( livea, 1, "Click on inner div" );
	equal( liveb, 1, "Click on inner div" );

	// This should trigger one submit
	submit = 0; div = 0; livea = 0; liveb = 0;
	jQuery("div#nothiddendivchild").trigger("submit");
	equal( submit, 1, "Submit on div" );
	equal( div, 0, "Submit on div" );
	equal( livea, 0, "Submit on div" );
	equal( liveb, 0, "Submit on div" );

	// Make sure no other events were removed in the process
	submit = 0; div = 0; livea = 0; liveb = 0;
	jQuery("div#nothiddendivchild").trigger("click");
	equal( submit, 0, "die Click on inner div" );
	equal( div, 2, "die Click on inner div" );
	equal( livea, 1, "die Click on inner div" );
	equal( liveb, 1, "die Click on inner div" );

	// Now make sure that the removal works
	submit = 0; div = 0; livea = 0; liveb = 0;
	jQuery("div#nothiddendivchild").die("click");
	jQuery("div#nothiddendivchild").trigger("click");
	equal( submit, 0, "die Click on inner div" );
	equal( div, 2, "die Click on inner div" );
	equal( livea, 1, "die Click on inner div" );
	equal( liveb, 0, "die Click on inner div" );

	// Make sure that the click wasn't removed too early
	submit = 0; div = 0; livea = 0; liveb = 0;
	jQuery("div#nothiddendiv").trigger("click");
	equal( submit, 0, "die Click on inner div" );
	equal( div, 1, "die Click on inner div" );
	equal( livea, 1, "die Click on inner div" );
	equal( liveb, 0, "die Click on inner div" );

	// Make sure that stopPropgation doesn't stop live events
	submit = 0; div = 0; livea = 0; liveb = 0;
	jQuery("div#nothiddendivchild").live("click", function(e){ liveb++; e.stopPropagation(); });
	jQuery("div#nothiddendivchild").trigger("click");
	equal( submit, 0, "stopPropagation Click on inner div" );
	equal( div, 1, "stopPropagation Click on inner div" );
	equal( livea, 0, "stopPropagation Click on inner div" );
	equal( liveb, 1, "stopPropagation Click on inner div" );

	// Make sure click events only fire with primary click
	submit = 0; div = 0; livea = 0; liveb = 0;
	event = jQuery.Event("click");
	event.button = 1;
	jQuery("div#nothiddendiv").trigger(event);

	equal( livea, 0, "live secondary click" );

	jQuery("div#nothiddendivchild").die("click");
	jQuery("div#nothiddendiv").die("click");
	jQuery("div").die("click");
	jQuery("div").die("submit");

	// Test binding with a different context
	clicked = 0, container = jQuery("#qunit-fixture")[0];
	jQuery("#foo", container).live("click", function(e){ clicked++; });
	jQuery("div").trigger("click");
	jQuery("#foo").trigger("click");
	jQuery("#qunit-fixture").trigger("click");
	jQuery("body").trigger("click");
	equal( clicked, 2, "live with a context" );

	// Test unbinding with a different context
	jQuery("#foo", container).die("click");
	jQuery("#foo").trigger("click");
	equal( clicked, 2, "die with a context");

	// Test binding with event data
	jQuery("#foo").live("click", true, function(e){ equal( e.data, true, "live with event data" ); });
	jQuery("#foo").trigger("click").die("click");

	// Test binding with trigger data
	jQuery("#foo").live("click", function(e, data){ equal( data, true, "live with trigger data" ); });
	jQuery("#foo").trigger("click", true).die("click");

	// Test binding with different this object
	jQuery("#foo").live("click", jQuery.proxy(function(e){ equal( this.foo, "bar", "live with event scope" ); }, { foo: "bar" }));
	jQuery("#foo").trigger("click").die("click");

	// Test binding with different this object, event data, and trigger data
	jQuery("#foo").live("click", true, jQuery.proxy(function(e, data){
		equal( e.data, true, "live with with different this object, event data, and trigger data" );
		equal( this["foo"], "bar", "live with with different this object, event data, and trigger data" );
		equal( data, true, "live with with different this object, event data, and trigger data");
	}, { "foo": "bar" }));
	jQuery("#foo").trigger("click", true).die("click");

	// Verify that return false prevents default action
	jQuery("#anchor2").live("click", function(){ return false; });
	hash = window.location.hash;
	jQuery("#anchor2").trigger("click");
	equal( window.location.hash, hash, "return false worked" );
	jQuery("#anchor2").die("click");

	// Verify that .preventDefault() prevents default action
	jQuery("#anchor2").live("click", function(e){ e.preventDefault(); });
	hash = window.location.hash;
	jQuery("#anchor2").trigger("click");
	equal( window.location.hash, hash, "e.preventDefault() worked" );
	jQuery("#anchor2").die("click");

	// Test binding the same handler to multiple points
	called = 0;
	function callback(){ called++; return false; }

	jQuery("#nothiddendiv").live("click", callback);
	jQuery("#anchor2").live("click", callback);

	jQuery("#nothiddendiv").trigger("click");
	equal( called, 1, "Verify that only one click occurred." );

	called = 0;
	jQuery("#anchor2").trigger("click");
	equal( called, 1, "Verify that only one click occurred." );

	// Make sure that only one callback is removed
	jQuery("#anchor2").die("click", callback);

	called = 0;
	jQuery("#nothiddendiv").trigger("click");
	equal( called, 1, "Verify that only one click occurred." );

	called = 0;
	jQuery("#anchor2").trigger("click");
	equal( called, 0, "Verify that no click occurred." );

	// Make sure that it still works if the selector is the same,
	// but the event type is different
	jQuery("#nothiddendiv").live("foo", callback);

	// Cleanup
	jQuery("#nothiddendiv").die("click", callback);

	called = 0;
	jQuery("#nothiddendiv").trigger("click");
	equal( called, 0, "Verify that no click occurred." );

	called = 0;
	jQuery("#nothiddendiv").trigger("foo");
	equal( called, 1, "Verify that one foo occurred." );

	// Cleanup
	jQuery("#nothiddendiv").die("foo", callback);

	// Make sure we don't loose the target by DOM modifications
	// after the bubble already reached the liveHandler
	livec = 0, elemDiv = jQuery("#nothiddendivchild").html("<span></span>").get(0);

	jQuery("#nothiddendivchild").live("click", function(e){ jQuery("#nothiddendivchild").html(""); });
	jQuery("#nothiddendivchild").live("click", function(e){ if(e.target) {livec++;} });

	jQuery("#nothiddendiv span").click();
	equal( jQuery("#nothiddendiv span").length, 0, "Verify that first handler occurred and modified the DOM." );
	equal( livec, 1, "Verify that second handler occurred even with nuked target." );

	// Cleanup
	jQuery("#nothiddendivchild").die("click");

	// Verify that .live() ocurs and cancel buble in the same order as
	// we would expect .bind() and .click() without delegation
	lived = 0, livee = 0;

	// bind one pair in one order
	jQuery("span#liveSpan1 a").live("click", function(){ lived++; return false; });
	jQuery("span#liveSpan1").live("click", function(){ livee++; });

	jQuery("span#liveSpan1 a").click();
	equal( lived, 1, "Verify that only one first handler occurred." );
	equal( livee, 0, "Verify that second handler doesn't." );

	// and one pair in inverse
	jQuery("span#liveSpan2").live("click", function(){ livee++; });
	jQuery("span#liveSpan2 a").live("click", function(){ lived++; return false; });

	lived = 0;
	livee = 0;
	jQuery("span#liveSpan2 a").click();
	equal( lived, 1, "Verify that only one first handler occurred." );
	equal( livee, 0, "Verify that second handler doesn't." );

	// Cleanup
	jQuery("span#liveSpan1 a").die("click");
	jQuery("span#liveSpan1").die("click");
	jQuery("span#liveSpan2 a").die("click");
	jQuery("span#liveSpan2").die("click");

	// Test this, target and currentTarget are correct
	jQuery("span#liveSpan1").live("click", function(e){
		equal( this.id, "liveSpan1", "Check the this within a live handler" );
		equal( e.currentTarget.id, "liveSpan1", "Check the event.currentTarget within a live handler" );
		if ( e.delegateTarget !== undefined ) {
			equal( e.delegateTarget, document, "Check the event.delegateTarget within a live handler" );
		} else {
			ok( true, "No delegateTarget before jQuery 1.7" );
		}
		equal( e.target.nodeName.toUpperCase(), "A", "Check the event.target within a live handler" );
	});

	jQuery("span#liveSpan1 a").click();

	jQuery("span#liveSpan1").die("click");

	// Work with deep selectors
	livee = 0;

	function clickB(){ livee++; }

	jQuery("#nothiddendiv div").live("click", function(){ livee++; });
	jQuery("#nothiddendiv div").live("click", clickB);
	jQuery("#nothiddendiv div").live("mouseover", function(){ livee++; });

	equal( livee, 0, "No clicks, deep selector." );

	livee = 0;
	jQuery("#nothiddendivchild").trigger("click");
	equal( livee, 2, "Click, deep selector." );

	livee = 0;
	jQuery("#nothiddendivchild").trigger("mouseover");
	equal( livee, 1, "Mouseover, deep selector." );

	jQuery("#nothiddendiv div").die("mouseover");

	livee = 0;
	jQuery("#nothiddendivchild").trigger("click");
	equal( livee, 2, "Click, deep selector." );

	livee = 0;
	jQuery("#nothiddendivchild").trigger("mouseover");
	equal( livee, 0, "Mouseover, deep selector." );

	jQuery("#nothiddendiv div").die("click", clickB);

	livee = 0;
	jQuery("#nothiddendivchild").trigger("click");
	equal( livee, 1, "Click, deep selector." );

	jQuery("#nothiddendiv div").die("click");

	// blur a non-input element, we should force-fire its handlers
	// regardless of whether it's burring or not (unlike browsers)
	jQuery("#nothiddendiv div")
		.live("blur", function(){
			ok( true, "Live div trigger blur." );
		})
		.trigger("blur")
		.die("blur");
});

test( "die all bound events", function(){
	expect(1);

	var count = 0, div = jQuery("div#nothiddendivchild");

	div.live("click submit", function(){ count++; });
	div.die();

	div.trigger("click");
	div.trigger("submit");

	equal( count, 0, "Make sure no events were triggered." );
});

test( "live with multiple events", function(){
	expect(1);

	var count = 0, div = jQuery("div#nothiddendivchild");

	div.live("click submit", function(){ count++; });

	div.trigger("click");
	div.trigger("submit");

	equal( count, 2, "Make sure both the click and submit were triggered." );

	// manually clean up events from elements outside the fixture
	div.die();
});

test( "live with namespaces", function(){
	expect(15);

	var count1 = 0, count2 = 0;

	jQuery("#liveSpan1").live("foo.bar", function(e){
		equal( e.namespace, "bar", "namespace is bar" );
		count1++;
	});

	jQuery("#liveSpan1").live("foo.zed", function(e){
		equal( e.namespace, "zed", "namespace is zed" );
		count2++;
	});

	jQuery("#liveSpan1").trigger("foo.bar");
	equal( count1, 1, "Got live foo.bar" );
	equal( count2, 0, "Got live foo.bar" );

	count1 = 0; count2 = 0;

	jQuery("#liveSpan1").trigger("foo.zed");
	equal( count1, 0, "Got live foo.zed" );
	equal( count2, 1, "Got live foo.zed" );

	//remove one
	count1 = 0; count2 = 0;

	jQuery("#liveSpan1").die("foo.zed");
	jQuery("#liveSpan1").trigger("foo.bar");

	equal( count1, 1, "Got live foo.bar after dieing foo.zed" );
	equal( count2, 0, "Got live foo.bar after dieing foo.zed" );

	count1 = 0; count2 = 0;

	jQuery("#liveSpan1").trigger("foo.zed");
	equal( count1, 0, "Got live foo.zed" );
	equal( count2, 0, "Got live foo.zed" );

	//remove the other
	jQuery("#liveSpan1").die("foo.bar");

	count1 = 0; count2 = 0;

	jQuery("#liveSpan1").trigger("foo.bar");
	equal( count1, 0, "Did not respond to foo.bar after dieing it" );
	equal( count2, 0, "Did not respond to foo.bar after dieing it" );

	jQuery("#liveSpan1").trigger("foo.zed");
	equal( count1, 0, "Did not trigger foo.zed again" );
	equal( count2, 0, "Did not trigger foo.zed again" );
});

test( "live with change", function(){
	expect(8);

	var text, textChange, oldTextVal,
		password, passwordChange, oldPasswordVal,
		selectChange = 0,
		checkboxChange = 0,
		select = jQuery("select[name='S1']"),
		checkbox = jQuery("#check2"),
		checkboxFunction = function(){
			checkboxChange++;
		};

	select.live("change", function() {
		selectChange++;
	});
	checkbox.live("change", checkboxFunction);

	// test click on select

	// second click that changed it
	selectChange = 0;
	select[0].selectedIndex = select[0].selectedIndex ? 0 : 1;
	select.trigger("change");
	equal( selectChange, 1, "Change on click." );

	// test keys on select
	selectChange = 0;
	select[0].selectedIndex = select[0].selectedIndex ? 0 : 1;
	select.trigger("change");
	equal( selectChange, 1, "Change on keyup." );

	// test click on checkbox
	checkbox.trigger("change");
	equal( checkboxChange, 1, "Change on checkbox." );

	// test blur/focus on text
	text = jQuery("#name");
	textChange = 0;
	oldTextVal = text.val();
	text.live("change", function() {
		textChange++;
	});

	text.val(oldTextVal+"foo");
	text.trigger("change");
	equal( textChange, 1, "Change on text input." );

	text.val(oldTextVal);
	text.die("change");

	// test blur/focus on password
	password = jQuery("#name");
	passwordChange = 0;
	oldPasswordVal = password.val();
	password.live("change", function() {
		passwordChange++;
	});

	password.val(oldPasswordVal + "foo");
	password.trigger("change");
	equal( passwordChange, 1, "Change on password input." );

	password.val(oldPasswordVal);
	password.die("change");

	// make sure die works

	// die all changes
	selectChange = 0;
	select.die("change");
	select[0].selectedIndex = select[0].selectedIndex ? 0 : 1;
	select.trigger("change");
	equal( selectChange, 0, "Die on click works." );

	selectChange = 0;
	select[0].selectedIndex = select[0].selectedIndex ? 0 : 1;
	select.trigger("change");
	equal( selectChange, 0, "Die on keyup works." );

	// die specific checkbox
	checkbox.die("change", checkboxFunction);
	checkbox.trigger("change");
	equal( checkboxChange, 1, "Die on checkbox." );
});

test( "live with submit", function() {
	expect(7);

	var count1 = 0, count2 = 0;

	jQuery("#testForm").live("submit", function(ev) {
		count1++;
		ev.preventDefault();
	});

	jQuery("body").live("submit", function(ev) {
		count2++;
		ev.preventDefault();
	});

	jQuery("#testForm input[name=sub1]").submit();
	equal( count1, 1, "Verify form submit." );
	equal( count2, 1, "Verify body submit." );

	jQuery("#testForm input[name=sub1]").live("click", function(ev) {
		ok( true, "cancelling submit still calls click handler" );
	});

	jQuery("#testForm input[name=sub1]")[0].click();
	equal( count1, 2, "Verify form submit." );
	equal( count2, 2, "Verify body submit." );

	jQuery("#testForm button[name=sub4]")[0].click();
	equal( count1, 3, "Verify form submit." );
	equal( count2, 3, "Verify body submit." );

	jQuery("#testForm").die("submit");
	jQuery("#testForm input[name=sub1]").die("click");
	jQuery("body").die("submit");
});

test( "live with special events", function() {
	expect(13);

	jQuery.event.special["foo"] = {
		setup: function( data, namespaces, handler ) {
			ok( true, "Setup run." );
		},
		teardown: function( namespaces ) {
			ok( true, "Teardown run." );
		},
		add: function( handleObj ) {
			ok( true, "Add run." );
		},
		remove: function( handleObj ) {
			ok( true, "Remove run." );
		},
		_default: function( event, arg ) {
			ok( true, "Default run." );
		}
	};

	// Run: setup, add
	jQuery("#liveSpan1").live("foo.a", function(e){
		ok( true, "Handler 1 run." );
	});

	// Run: add
	jQuery("#liveSpan1").live("foo.b", function(e){
		ok( true, "Handler 2 run." );
	});

	// Run: Handler 1, Handler 2, Default
	jQuery("#liveSpan1").trigger("foo", 42);

	// Run: Handler 1, Default
	jQuery("#liveSpan1").trigger("foo.a", 42);

	// Run: remove
	jQuery("#liveSpan1").die("foo.a");

	// Run: Handler 2, Default
	jQuery("#liveSpan1").trigger("foo", 42);

	// Run: remove, teardown
	jQuery("#liveSpan1").die("foo");

	delete jQuery.event.special["foo"];
});

test( "toggle(Function, Function, ...)", function() {
	expect( 19 );

	var fns, data, $div, a, b,
		count = 0,
		first = 0,
		turn = 0,
		fn1 = function(e) { count++; },
		fn2 = function(e) { count--; },
		preventDefault = function(e) { e.preventDefault(); },
		link = jQuery("#mark");

	expectNoWarning( "jQuery.fn.toggle visibility unaffected", function() {
		jQuery("#foo").toggle( false );
		ok( jQuery("#foo").is(":hidden"), ".toggle(Boolean) unaffected" );
	});

	expectWarning( "jQuery.fn.toggle", function() {
		link.click(preventDefault).click().toggle(fn1, fn2).click().click().click().click().click();
		equal( count, 1, "Check for toggle(fn, fn)" );
	});

	jQuery("#firstp").toggle(function () {
		equal(arguments.length, 4, "toggle correctly passes through additional triggered arguments, see #1701" );
	}, function() {}).trigger("click", [ 1, 2, 3 ]);

	jQuery("#simon1").one("click", function() {
		ok( true, "Execute event only once" );
		jQuery(this).toggle(function() {
			equal( first++, 0, "toggle(Function,Function) assigned from within one('xxx'), see #1054" );
		}, function() {
			equal( first, 1, "toggle(Function,Function) assigned from within one('xxx'), see #1054" );
		});
		return false;
	}).click().click().click();

	fns = [
		function(){
			turn = 1;
		},
		function(){
			turn = 2;
		},
		function(){
			turn = 3;
		}
	];

	$div = jQuery("<div>&nbsp;</div>").toggle( fns[0], fns[1], fns[2] );
	$div.click();
	equal( turn, 1, "Trying toggle with 3 functions, attempt 1 yields 1");
	$div.click();
	equal( turn, 2, "Trying toggle with 3 functions, attempt 2 yields 2");
	$div.click();
	equal( turn, 3, "Trying toggle with 3 functions, attempt 3 yields 3");
	$div.click();
	equal( turn, 1, "Trying toggle with 3 functions, attempt 4 yields 1");
	$div.click();
	equal( turn, 2, "Trying toggle with 3 functions, attempt 5 yields 2");

	$div.unbind("click",fns[0]);
	data = jQuery._data( $div[0], "events" );
	ok( !data, "Unbinding one function from toggle unbinds them all");

	// manually clean up detached elements
	$div.remove();

	// Test Multi-Toggles
	a = [], b = [];
	$div = jQuery("<div/>");
	$div.toggle(function(){ a.push(1); }, function(){ a.push(2); });
	$div.click();
	deepEqual( a, [1], "Check that a click worked." );

	$div.toggle(function(){ b.push(1); }, function(){ b.push(2); });
	$div.click();
	deepEqual( a, [1,2], "Check that a click worked with a second toggle." );
	deepEqual( b, [1], "Check that a click worked with a second toggle." );

	$div.click();
	deepEqual( a, [1,2,1], "Check that a click worked with a second toggle, second click." );
	deepEqual( b, [1,2], "Check that a click worked with a second toggle, second click." );

	// manually clean up detached elements
	$div.remove();
});

test( "error() event method", function() {
	expect( 2 );

	expectWarning( "jQuery.fn.error()", function() {
		jQuery( "<img />" )
			.error(function(){
				ok( true, "Triggered error event" );
			})
			.error()
			.unbind( "error" )
			.error()
			.remove();
	});
});

test( "load() and unload() event methods", function() {
	expect( 5 );

	expectWarning( "jQuery.fn.load()", function() {
		jQuery( "<img />" )
			.load(function(){
				ok( true, "Triggered load event" );
			})
			.load()
			.unbind( "load" )
			.load()
			.remove();
	});

	expectWarning( "jQuery.fn.unload()", function() {
		jQuery( "<img />" )
			.unload(function(){
				ok( true, "Triggered unload event" );
			})
			.unload()
			.unbind( "unload" )
			.unload()
			.remove();
	});

	expectNoWarning( "ajax load", function() {
		stop();
		jQuery( "<div id=load138></div>" )
			.appendTo( "#qunit-fixture" )
			.load( "not-found.file", function() {
				jQuery( "#load138" ).remove();
				start();
			});
	});
});

test( "hover pseudo-event", function() {
	expect( 3 );

	expectWarning( "'hover' event", function() {
		var balance = 0;

		jQuery( "#firstp" )
			.bind( "hovercraft", function() {
				ok( false, "hovercraft is full of ills" );
			})
			.bind( "click.hover.me.not", function( e ) {
				equal( e.handleObj.namespace, "hover.me.not", "hover hack doesn't mangle namespaces" );
			})
			.bind("hover", function( e ) {
				if ( e.type === "mouseenter" ) {
					balance++;
				} else if ( e.type === "mouseleave" ) {
					balance--;
				} else {
					ok( false, "hover pseudo: unknown event type "+e.type );
				}
			})
			.trigger("click")
			.trigger("mouseenter")
			.trigger("mouseleave")
			.unbind("hover")
			.trigger("mouseenter");

		equal( balance, 0, "hover pseudo-event" );
	});
});

test( "ready event", function() {
	expect( 4 );

	expectWarning( "Setting a ready event", 1, function() {
		jQuery( document ).bind( "ready", function() {
			ok( true, "ready event was triggered" );
		})
		.trigger( "ready" )
		.unbind( "ready" );
	});

	expectNoWarning( "Custom ready event not on document", 1, function() {
		jQuery( "#foo" ).bind( "ready", function( e ) {
			ok( true, "custom ready event was triggered" );
		})
		.trigger( "ready" )
		.unbind( "ready" );
	});
});

test( "global events not on document", function() {
	expect( 11 );

	expectWarning( "Global ajax events", 1, function() {
		var events = "ajaxStart ajaxStop ajaxSend ajaxComplete ajaxError ajaxSuccess";

		// Attach to random element, just like old times
		jQuery( "#first" ).bind( events, function( e ) {
			ok( true, e.type + " on #first" );
		});

		// Ensure attach to document still fires
		jQuery( document ).bind( events, function( e ) {
			ok( true, e.type + " on document" );
		});
		stop();

		jQuery.ajax({
			url: "index.html",
			complete: function() {
				// Give events a chance to fire before we remove them
				setTimeout(function() {
					jQuery( "#first" ).add( document ).unbind( events );
					setTimeout( start, 10 );
				}, 10 );
			}
		});
	});
});

test( "event args on non-document ajax events (#113)", function() {

	expect( 2 );

	// Ensure all args are passed to non-document ajax events
	jQuery( "#first" ).bind( "ajaxError", function( e, jqXHR, options ) {
		equal( arguments.length, 4, "passed all args" );
		equal( options.url, "not_found_404.html", "matched URL" );
	});

	stop();
	jQuery.ajax({
		url: "not_found_404.html",
		complete: function() {
			jQuery( "#first" ).unbind( "ajaxError" );
			setTimeout( start, 10 );
		}
	});
});

// Support: IE<=8
// Need ES5 Object.defineProperty() to catch property access
if ( jQuery.event.dispatch && Object.defineProperties ) {

	test( "jQuery.event.handle", function() {
		expect( 2 );

		var matched = 0,
			container = document.getElementById("foo"),
			target = document.getElementById("anchor2");

		jQuery("#foo").bind( "click", function() {
			matched++;
		});

		expectWarning( "jQuery.event.handle", function() {
			jQuery.event.handle.call(
				container,
				new jQuery.Event( "click", { target: target })
			);
		});

		equal( matched, 1, "Event dispatched" );
	});

}
