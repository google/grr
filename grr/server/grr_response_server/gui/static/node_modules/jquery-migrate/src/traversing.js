var oldSelf = jQuery.fn.andSelf || jQuery.fn.addBack,
	oldFnFind = jQuery.fn.find;

jQuery.fn.andSelf = function() {
	migrateWarn("jQuery.fn.andSelf() replaced by jQuery.fn.addBack()");
	return oldSelf.apply( this, arguments );
};

jQuery.fn.find = function( selector ) {
	var ret = oldFnFind.apply( this, arguments );
	ret.context = this.context;
	ret.selector = this.selector ? this.selector + " " + selector : selector;
	return ret;
};
