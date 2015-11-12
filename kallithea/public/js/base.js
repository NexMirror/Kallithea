/**
Kallithea JS Files
**/
'use strict';

if (typeof console == "undefined" || typeof console.log == "undefined"){
    console = { log: function() {} }
}

/**
 * INJECT .format function into String
 * Usage: "My name is {0} {1}".format("Johny","Bravo")
 * Return "My name is Johny Bravo"
 * Inspired by https://gist.github.com/1049426
 */
String.prototype.format = function() {
    function format() {
        var str = this;
        var len = arguments.length+1;
        var safe = undefined;
        var arg = undefined;

        // For each {0} {1} {n...} replace with the argument in that position.  If
        // the argument is an object or an array it will be stringified to JSON.
        for (var i=0; i < len; arg = arguments[i++]) {
            safe = typeof arg === 'object' ? JSON.stringify(arg) : arg;
            str = str.replace(RegExp('\\{'+(i-1)+'\\}', 'g'), safe);
        }
        return str;
    }

    // Save a reference of what may already exist under the property native.
    // Allows for doing something like: if("".format.native) { /* use native */ }
    format.native = String.prototype.format;

    // Replace the prototype property
    return format;

}();

String.prototype.strip = function(char) {
    if(char === undefined){
        char = '\\s';
    }
    return this.replace(new RegExp('^'+char+'+|'+char+'+$','g'), '');
}

String.prototype.lstrip = function(char) {
    if(char === undefined){
        char = '\\s';
    }
    return this.replace(new RegExp('^'+char+'+'),'');
}

String.prototype.rstrip = function(char) {
    if(char === undefined){
        char = '\\s';
    }
    return this.replace(new RegExp(''+char+'+$'),'');
}

/* https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/indexOf#Polyfill
   under MIT license / public domain, see
   https://developer.mozilla.org/en-US/docs/MDN/About#Copyrights_and_licenses */
if(!Array.prototype.indexOf) {
    Array.prototype.indexOf = function (searchElement, fromIndex) {
        if ( this === undefined || this === null ) {
            throw new TypeError( '"this" is null or not defined' );
        }

        var length = this.length >>> 0; // Hack to convert object.length to a UInt32

        fromIndex = +fromIndex || 0;

        if (Math.abs(fromIndex) === Infinity) {
            fromIndex = 0;
        }

        if (fromIndex < 0) {
            fromIndex += length;
            if (fromIndex < 0) {
                fromIndex = 0;
            }
        }

        for (;fromIndex < length; fromIndex++) {
            if (this[fromIndex] === searchElement) {
                return fromIndex;
            }
        }

        return -1;
    };
}

/* https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/filter#Compatibility
   under MIT license / public domain, see
   https://developer.mozilla.org/en-US/docs/MDN/About#Copyrights_and_licenses */
if (!Array.prototype.filter)
{
    Array.prototype.filter = function(fun /*, thisArg */)
    {
        if (this === void 0 || this === null)
            throw new TypeError();

        var t = Object(this);
        var len = t.length >>> 0;
        if (typeof fun !== "function")
            throw new TypeError();

        var res = [];
        var thisArg = arguments.length >= 2 ? arguments[1] : void 0;
        for (var i = 0; i < len; i++)
        {
            if (i in t)
            {
                var val = t[i];

                // NOTE: Technically this should Object.defineProperty at
                //       the next index, as push can be affected by
                //       properties on Object.prototype and Array.prototype.
                //       But that method's new, and collisions should be
                //       rare, so use the more-compatible alternative.
                if (fun.call(thisArg, val, i, t))
                    res.push(val);
            }
        }

        return res;
    };
}

/**
 * A customized version of PyRoutes.JS from https://pypi.python.org/pypi/pyroutes.js/
 * which is copyright Stephane Klein and was made available under the BSD License.
 *
 * Usage pyroutes.url('mark_error_fixed',{"error_id":error_id}) // /mark_error_fixed/<error_id>
 */
var pyroutes = (function() {
    var matchlist = {};
    var sprintf = (function() {
        function get_type(variable) {
            return Object.prototype.toString.call(variable).slice(8, -1).toLowerCase();
        }
        function str_repeat(input, multiplier) {
            for (var output = []; multiplier > 0; output[--multiplier] = input) {/* do nothing */}
            return output.join('');
        }

        var str_format = function() {
            if (!str_format.cache.hasOwnProperty(arguments[0])) {
                str_format.cache[arguments[0]] = str_format.parse(arguments[0]);
            }
            return str_format.format.call(null, str_format.cache[arguments[0]], arguments);
        };

        str_format.format = function(parse_tree, argv) {
            var cursor = 1, tree_length = parse_tree.length, node_type = '', arg, output = [], i, k, match, pad, pad_character, pad_length;
            for (i = 0; i < tree_length; i++) {
                node_type = get_type(parse_tree[i]);
                if (node_type === 'string') {
                    output.push(parse_tree[i]);
                }
                else if (node_type === 'array') {
                    match = parse_tree[i]; // convenience purposes only
                    if (match[2]) { // keyword argument
                        arg = argv[cursor];
                        for (k = 0; k < match[2].length; k++) {
                            if (!arg.hasOwnProperty(match[2][k])) {
                                throw(sprintf('[sprintf] property "%s" does not exist', match[2][k]));
                            }
                            arg = arg[match[2][k]];
                        }
                    }
                    else if (match[1]) { // positional argument (explicit)
                        arg = argv[match[1]];
                    }
                    else { // positional argument (implicit)
                        arg = argv[cursor++];
                    }

                    if (/[^s]/.test(match[8]) && (get_type(arg) != 'number')) {
                        throw(sprintf('[sprintf] expecting number but found %s', get_type(arg)));
                    }
                    switch (match[8]) {
                        case 'b': arg = arg.toString(2); break;
                        case 'c': arg = String.fromCharCode(arg); break;
                        case 'd': arg = parseInt(arg, 10); break;
                        case 'e': arg = match[7] ? arg.toExponential(match[7]) : arg.toExponential(); break;
                        case 'f': arg = match[7] ? parseFloat(arg).toFixed(match[7]) : parseFloat(arg); break;
                        case 'o': arg = arg.toString(8); break;
                        case 's': arg = ((arg = String(arg)) && match[7] ? arg.substring(0, match[7]) : arg); break;
                        case 'u': arg = Math.abs(arg); break;
                        case 'x': arg = arg.toString(16); break;
                        case 'X': arg = arg.toString(16).toUpperCase(); break;
                    }
                    arg = (/[def]/.test(match[8]) && match[3] && arg >= 0 ? '+'+ arg : arg);
                    pad_character = match[4] ? match[4] == '0' ? '0' : match[4].charAt(1) : ' ';
                    pad_length = match[6] - String(arg).length;
                    pad = match[6] ? str_repeat(pad_character, pad_length) : '';
                    output.push(match[5] ? arg + pad : pad + arg);
                }
            }
            return output.join('');
        };

        str_format.cache = {};

        str_format.parse = function(fmt) {
            var _fmt = fmt, match = [], parse_tree = [], arg_names = 0;
            while (_fmt) {
                if ((match = /^[^\x25]+/.exec(_fmt)) !== null) {
                    parse_tree.push(match[0]);
                }
                else if ((match = /^\x25{2}/.exec(_fmt)) !== null) {
                    parse_tree.push('%');
                }
                else if ((match = /^\x25(?:([1-9]\d*)\$|\(([^\)]+)\))?(\+)?(0|'[^$])?(-)?(\d+)?(?:\.(\d+))?([b-fosuxX])/.exec(_fmt)) !== null) {
                    if (match[2]) {
                        arg_names |= 1;
                        var field_list = [], replacement_field = match[2], field_match = [];
                        if ((field_match = /^([a-z_][a-z_\d]*)/i.exec(replacement_field)) !== null) {
                            field_list.push(field_match[1]);
                            while ((replacement_field = replacement_field.substring(field_match[0].length)) !== '') {
                                if ((field_match = /^\.([a-z_][a-z_\d]*)/i.exec(replacement_field)) !== null) {
                                    field_list.push(field_match[1]);
                                }
                                else if ((field_match = /^\[(\d+)\]/.exec(replacement_field)) !== null) {
                                    field_list.push(field_match[1]);
                                }
                                else {
                                    throw('[sprintf] huh?');
                                }
                            }
                        }
                        else {
                            throw('[sprintf] huh?');
                        }
                        match[2] = field_list;
                    }
                    else {
                        arg_names |= 2;
                    }
                    if (arg_names === 3) {
                        throw('[sprintf] mixing positional and named placeholders is not (yet) supported');
                    }
                    parse_tree.push(match);
                }
                else {
                    throw('[sprintf] huh?');
                }
                _fmt = _fmt.substring(match[0].length);
            }
            return parse_tree;
        };

        return str_format;
    })();

    var vsprintf = function(fmt, argv) {
        argv.unshift(fmt);
        return sprintf.apply(null, argv);
    };
    return {
        'url': function(route_name, params) {
            var result = route_name;
            if (typeof(params) != 'object'){
                params = {};
            }
            if (matchlist.hasOwnProperty(route_name)) {
                var route = matchlist[route_name];
                // param substitution
                for(var i=0; i < route[1].length; i++) {
                   if (!params.hasOwnProperty(route[1][i]))
                        throw new Error(route[1][i] + ' missing in "' + route_name + '" route generation');
                }
                result = sprintf(route[0], params);

                var ret = [];
                //extra params => GET
                for(var param in params){
                    if (route[1].indexOf(param) == -1){
                        ret.push(encodeURIComponent(param) + "=" + encodeURIComponent(params[param]));
                    }
                }
                var _parts = ret.join("&");
                if(_parts){
                    result = result +'?'+ _parts
                }
            }

            return result;
        },
        'register': function(route_name, route_tmpl, req_params) {
            if (typeof(req_params) != 'object') {
                req_params = [];
            }
            var keys = [];
            for (var i=0; i < req_params.length; i++) {
                keys.push(req_params[i]);
            }
            matchlist[route_name] = [
                unescape(route_tmpl),
                keys
            ]
        },
        '_routes': function(){
            return matchlist;
        }
    }
})();


/**
 * GLOBAL YUI Shortcuts
 */
var YUD = YAHOO.util.Dom;
var YUE = YAHOO.util.Event;

/* Invoke all functions in callbacks */
var _run_callbacks = function(callbacks){
    if (callbacks !== undefined){
        var _l = callbacks.length;
        for (var i=0;i<_l;i++){
            var func = callbacks[i];
            if(typeof(func)=='function'){
                try{
                    func();
                }catch (err){};
            }
        }
    }
}

/**
 * turns objects into GET query string
 */
var _toQueryString = function(o) {
    if(typeof o !== 'object') {
        return false;
    }
    var _p, _qs = [];
    for(_p in o) {
        _qs.push(encodeURIComponent(_p) + '=' + encodeURIComponent(o[_p]));
    }
    return _qs.join('&');
};

/**
 * Load HTML into DOM using Ajax
 *
 * @param $target: load html async and place it (or an error message) here
 * @param success: success callback function
 * @param args: query parameters to pass to url
 */
function asynchtml(url, $target, success, args){
    if(args===undefined){
        args=null;
    }
    $target.html(_TM['Loading ...']).css('opacity','0.3');

    return $.ajax({url: url, data: args, headers: {'X-PARTIAL-XHR': '1'}, cache: false, dataType: 'html'})
        .done(function(html) {
                $target.html(html);
                $target.css('opacity','1.0');
                //execute the given original callback
                if (success !== undefined && success) {
                    success();
                }
            })
        .fail(function(jqXHR, textStatus, errorThrown) {
                if (textStatus == "abort")
                    return;
                $target.html('<span class="error_red">ERROR: {0}</span>'.format(textStatus));
                $target.css('opacity','1.0');
            })
        ;
};

var ajaxGET = function(url, success, failure) {
    if(failure === undefined) {
        failure = function(jqXHR, textStatus, errorThrown) {
                if (textStatus != "abort")
                    alert("Ajax GET error: " + textStatus);
            };
    }
    return $.ajax({url: url, headers: {'X-PARTIAL-XHR': '1'}, cache: false})
        .done(success)
        .fail(failure);
};

var ajaxPOST = function(url, postData, success, failure) {
    postData['_authentication_token'] = _authentication_token;
    var postData = _toQueryString(postData);
    if(failure === undefined) {
        failure = function(jqXHR, textStatus, errorThrown) {
                if (textStatus != "abort")
                    alert("Error posting to server: " + textStatus);
            };
    }
    return $.ajax({url: url, data: postData, type: 'POST', headers: {'X-PARTIAL-XHR': '1'}, cache: false})
        .done(success)
        .fail(failure);
};


/**
 * activate .show_more links
 * the .show_more must have an id that is the the id of an element to hide prefixed with _
 * the parentnode will be displayed
 */
var show_more_event = function(){
    $('.show_more').click(function(e){
        var el = e.currentTarget;
        $('#' + el.id.substring(1)).hide();
        $(el.parentNode).show();
    });
};

/**
 * activate .lazy-cs mouseover for showing changeset tooltip
 */
var show_changeset_tooltip = function(){
    $('.lazy-cs').mouseover(function(e){
        var $target = $(e.currentTarget);
        var rid = $target.attr('raw_id');
        var repo_name = $target.attr('repo_name');
        if(rid && !$target.hasClass('tooltip')){
            _show_tooltip(e, _TM['loading ...']);
            var url = pyroutes.url('changeset_info', {"repo_name": repo_name, "revision": rid});
            ajaxGET(url, function(json){
                    $target.addClass('tooltip');
                    _show_tooltip(e, json['message']);
                    _activate_tooltip($target);
                });
        }
    });
};

var _onSuccessFollow = function(target){
    var $target = $(target);
    var $f_cnt = $('#current_followers_count');
    if ($target.hasClass('follow')) {
        $target.removeClass('follow').addClass('following');
        $target.prop('title', _TM['Stop following this repository']);
        if ($f_cnt.html()) {
            var cnt = Number($f_cnt.html())+1;
            $f_cnt.html(cnt);
        }
    } else {
        $target.removeClass('following').addClass('follow');
        $target.prop('title', _TM['Start following this repository']);
        if ($f_cnt.html()) {
            var cnt = Number($f_cnt.html())-1;
            $f_cnt.html(cnt);
        }
    }
}

var toggleFollowingRepo = function(target, follows_repo_id){
    var args = 'follows_repo_id=' + follows_repo_id;
    args += '&amp;_authentication_token=' + _authentication_token;
    $.post(TOGGLE_FOLLOW_URL, args, function(data){
            _onSuccessFollow(target);
        });
    return false;
};

var showRepoSize = function(target, repo_name){
    var args = '_authentication_token=' + _authentication_token;

    if(!$("#" + target).hasClass('loaded')){
        $("#" + target).html(_TM['Loading ...']);
        var url = pyroutes.url('repo_size', {"repo_name":repo_name});
        $.post(url, args, function(data) {
            $("#" + target).html(data);
            $("#" + target).addClass('loaded');
        });
    }
    return false;
};

/**
 * tooltips
 */

var tooltip_activate = function(){
    $(document).ready(_init_tooltip);
};

var _activate_tooltip = function($tt){
    $tt.mouseover(_show_tooltip);
    $tt.mousemove(_move_tooltip);
    $tt.mouseout(_close_tooltip);
};

var _init_tooltip = function(){
    var $tipBox = $('#tip-box');
    if(!$tipBox.length){
        $tipBox = $('<div id="tip-box"></div>');
        $(document.body).append($tipBox);
    }

    $tipBox.hide();
    $tipBox.css('position', 'absolute');
    $tipBox.css('max-width', '600px');

    _activate_tooltip($('.tooltip'));
};

var _show_tooltip = function(e, tipText, safe){
    e.stopImmediatePropagation();
    var el = e.currentTarget;
    var $el = $(el);
    if(tipText){
        // just use it
    } else if(el.tagName.toLowerCase() === 'img'){
        tipText = el.alt ? el.alt : '';
    } else {
        tipText = el.title ? el.title : '';
        safe = safe || $el.hasClass("safe-html-title");
    }

    if(tipText !== ''){
        // save org title
        $el.attr('tt_title', tipText);
        // reset title to not show org tooltips
        $el.prop('title', '');

        var $tipBox = $('#tip-box');
        if (safe) {
            $tipBox.html(tipText);
        } else {
            $tipBox.text(tipText);
        }
        $tipBox.css('display', 'block');
    }
};

var _move_tooltip = function(e){
    e.stopImmediatePropagation();
    var $tipBox = $('#tip-box');
    $tipBox.css('top', (e.pageY + 15) + 'px');
    $tipBox.css('left', (e.pageX + 15) + 'px');
};

var _close_tooltip = function(e){
    e.stopImmediatePropagation();
    var $tipBox = $('#tip-box');
    $tipBox.hide();
    var el = e.currentTarget;
    $(el).prop('title', $(el).attr('tt_title'));
};

/**
 * Quick filter widget
 *
 * @param target: filter input target
 * @param nodes: list of nodes in html we want to filter.
 * @param display_element function that takes current node from nodes and
 *    does hide or show based on the node
 */
var q_filter = (function() {
    var _namespace = {};
    var namespace = function (target) {
        if (!(target in _namespace)) {
            _namespace[target] = {};
        }
        return _namespace[target];
    };
    return function (target, $nodes, display_element) {
        var $nodes = $nodes;
        var $q_filter_field = $('#' + target);
        var F = namespace(target);

        $q_filter_field.keyup(function (e) {
            clearTimeout(F.filterTimeout);
            F.filterTimeout = setTimeout(F.updateFilter, 600);
        });

        F.filterTimeout = null;

        F.updateFilter = function () {
            // Reset timeout
            F.filterTimeout = null;

            var obsolete = [];

            var req = $q_filter_field.val().toLowerCase();

            var showing = 0;
            $nodes.each(function () {
                var n = this;
                var target_element = display_element(n);
                if (req && n.innerHTML.toLowerCase().indexOf(req) == -1) {
                    $(target_element).hide();
                }
                else {
                    $(target_element).show();
                    showing += 1;
                }
            });

            $('#repo_count').html(showing);
            /* FIXME: don't hardcode */
        }
    }
})();


/**
 * Comment handling
 */

// move comments to their right location, inside new trs
function move_comments($anchorcomments) {
    $anchorcomments.each(function(i, anchorcomment) {
        var $anchorcomment = $(anchorcomment);
        var target_id = $anchorcomment.data('target-id');
        var $comment_div = _get_add_comment_div(target_id);
        var f_path = $anchorcomment.data('f_path');
        var line_no = $anchorcomment.data('line_no');
        if ($comment_div[0]) {
            $comment_div.append($anchorcomment.children());
            _comment_div_append_add($comment_div, f_path, line_no);
        } else {
           $anchorcomment.before("Comment to {0} line {1} which is outside the diff context:".format(f_path || '?', line_no || '?'));
        }
    });
    linkInlineComments($('.firstlink'), $('.comment:first-child'));
}

// comment bubble was clicked - insert new tr and show form
function show_comment_form($bubble) {
    var children = $bubble.closest('tr.line').children('[id]');
    var line_td_id = children[children.length - 1].id;
    var $comment_div = _get_add_comment_div(line_td_id);
    var f_path = $bubble.closest('div.full_f_path').data('f_path');
    var parts = line_td_id.split('_');
    var line_no = parts[parts.length-1];
    comment_div_state($comment_div, f_path, line_no, true);
}

// return comment div for target_id - add it if it doesn't exist yet
function _get_add_comment_div(target_id) {
    var comments_box_id = 'comments-' + target_id;
    var $comments_box = $('#' + comments_box_id);
    if (!$comments_box.length) {
        var html = '<tr><td id="{0}" colspan="3" class="inline-comments"></td></tr>'.format(comments_box_id);
        $('#' + target_id).closest('tr').after(html);
        $comments_box = $('#' + comments_box_id);
    }
    return $comments_box;
}

// set $comment_div state - showing or not showing form and Add button
function comment_div_state($comment_div, f_path, line_no, show_form) {
    var $forms = $comment_div.children('.comment-inline-form');
    var $buttonrow = $comment_div.children('.add-button-row');
    var $comments = $comment_div.children('.comment');
    if (show_form) {
        if (!$forms.length) {
            _comment_div_append_form($comment_div, f_path, line_no);
        }
    } else {
        $forms.remove();
    }
    $buttonrow.remove();
    if ($comments.length && !show_form) {
        _comment_div_append_add($comment_div, f_path, line_no);
    }
}

// append an Add button to $comment_div and hook it up to show form
function _comment_div_append_add($comment_div, f_path, line_no) {
    var addlabel = TRANSLATION_MAP['Add Another Comment'];
    var $add = $('<div class="add-button-row"><span class="btn btn-mini add-button">{0}</span></div>'.format(addlabel));
    $comment_div.append($add);
    $add.children('.add-button').click(function(e) {
        comment_div_state($comment_div, f_path, line_no, true);
    });
}

// append a comment form to $comment_div
function _comment_div_append_form($comment_div, f_path, line_no) {
    var $form_div = $($('#comment-inline-form-template').html().format(f_path, line_no))
        .addClass('comment-inline-form');
    $comment_div.append($form_div);
    var $form = $comment_div.find("form");

    $form.submit(function(e) {
        e.preventDefault();

        var text = $('#text_'+line_no).val();
        if (!text){
            return;
        }

        $form.find('.submitting-overlay').show();

        var success = function(json_data) {
            $comment_div.append(json_data['rendered_text']);
            comment_div_state($comment_div, f_path, line_no, false);
            linkInlineComments($('.firstlink'), $('.comment:first-child'));
        };
        var postData = {
            'text': text,
            'f_path': f_path,
            'line': line_no
        };
        ajaxPOST(AJAX_COMMENT_URL, postData, success);
    });

    $('#preview-btn_'+line_no).click(function(e){
        var text = $('#text_'+line_no).val();
        if(!text){
            return
        }
        $('#preview-box_'+line_no).addClass('unloaded');
        $('#preview-box_'+line_no).html(_TM['Loading ...']);
        $('#edit-container_'+line_no).hide();
        $('#edit-btn_'+line_no).show();
        $('#preview-container_'+line_no).show();
        $('#preview-btn_'+line_no).hide();

        var url = pyroutes.url('changeset_comment_preview', {'repo_name': REPO_NAME});
        var post_data = {'text': text};
        ajaxPOST(url, post_data, function(html) {
            $('#preview-box_'+line_no).html(html);
            $('#preview-box_'+line_no).removeClass('unloaded');
        })
    })
    $('#edit-btn_'+line_no).click(function(e) {
        $('#edit-container_'+line_no).show();
        $('#edit-btn_'+line_no).hide();
        $('#preview-container_'+line_no).hide();
        $('#preview-btn_'+line_no).show();
    })

    // create event for hide button
    $form.find('.hide-inline-form').click(function(e) {
        comment_div_state($comment_div, f_path, line_no, false);
    });

    setTimeout(function() {
        // callbacks
        tooltip_activate();
        MentionsAutoComplete($('#text_'+line_no), $('#mentions_container_'+line_no),
                             _USERS_AC_DATA);
        $('#text_'+line_no).focus();
    }, 10);
}


function deleteComment(comment_id) {
    var url = AJAX_COMMENT_DELETE_URL.replace('__COMMENT_ID__', comment_id);
    var postData = {'_method': 'delete'};
    var success = function(o) {
        $('#comment-'+comment_id).remove();
        // Ignore that this might leave a stray Add button (or have a pending form with another comment) ...
    }
    ajaxPOST(url, postData, success);
}


/**
 * Double link comments
 */
var linkInlineComments = function($firstlinks, $comments){
    if ($comments.length > 0) {
        $firstlinks.html('<a href="#{0}">First comment</a>'.format($comments.prop('id')));
    }
    if ($comments.length <= 1) {
        return;
    }

    $comments.each(function(i, e){
            var prev = '';
            if (i > 0){
                var prev_anchor = $($comments.get(i-1)).prop('id');
                prev = '<a href="#{0}">Previous comment</a>'.format(prev_anchor);
            }
            var next = '';
            if (i+1 < $comments.length){
                var next_anchor = $($comments.get(i+1)).prop('id');
                next = '<a href="#{0}">Next comment</a>'.format(next_anchor);
            }
            $(this).find('.comment-prev-next-links').html(
                '<div class="prev-comment">{0}</div>'.format(prev) +
                '<div class="next-comment">{0}</div>'.format(next));
        });
}

/* activate files.html stuff */
var fileBrowserListeners = function(current_url, node_list_url, url_base){
    var current_url_branch = "?branch=__BRANCH__";

    $('#stay_at_branch').on('click',function(e){
        if(e.currentTarget.checked){
            var uri = current_url_branch;
            uri = uri.replace('__BRANCH__',e.currentTarget.value);
            window.location = uri;
        }
        else{
            window.location = current_url;
        }
    });

    var $node_filter = $('#node_filter');

    var filterTimeout = null;
    var nodes = null;

    var initFilter = function(){
        $('#node_filter_box_loading').show();
        $('#search_activate_id').hide();
        $('#add_node_id').hide();
        $.ajax({url: node_list_url, headers: {'X-PARTIAL-XHR': '1'}, cache: false})
            .done(function(json) {
                    nodes = json.nodes;
                    $('#node_filter_box_loading').hide();
                    $('#node_filter_box').show();
                    $node_filter.focus();
                    if($node_filter.hasClass('init')){
                        $node_filter.val('');
                        $node_filter.removeClass('init');
                    }
                })
            .fail(function() {
                    console.log('fileBrowserListeners initFilter failed to load');
                })
        ;
    }

    var updateFilter = function(e) {
        return function(){
            // Reset timeout
            filterTimeout = null;
            var query = e.currentTarget.value.toLowerCase();
            var match = [];
            var matches = 0;
            var matches_max = 20;
            if (query != ""){
                for(var i=0;i<nodes.length;i++){
                    var pos = nodes[i].name.toLowerCase().indexOf(query);
                    if(query && pos != -1){
                        matches++
                        //show only certain amount to not kill browser
                        if (matches > matches_max){
                            break;
                        }

                        var n = nodes[i].name;
                        var t = nodes[i].type;
                        var n_hl = n.substring(0,pos)
                            + "<b>{0}</b>".format(n.substring(pos,pos+query.length))
                            + n.substring(pos+query.length);
                        var new_url = url_base.replace('__FPATH__',n);
                        match.push('<tr><td><a class="browser-{0}" href="{1}">{2}</a></td><td colspan="5"></td></tr>'.format(t,new_url,n_hl));
                    }
                    if(match.length >= matches_max){
                        match.push('<tr><td>{0}</td><td colspan="5"></td></tr>'.format(_TM['Search truncated']));
                        break;
                    }
                }
            }
            if(query != ""){
                $('#tbody').hide();
                $('#tbody_filtered').show();

                if (match.length==0){
                  match.push('<tr><td>{0}</td><td colspan="5"></td></tr>'.format(_TM['No matching files']));
                }

                $('#tbody_filtered').html(match.join(""));
            }
            else{
                $('#tbody').show();
                $('#tbody_filtered').hide();
            }
        }
    };

    $('#filter_activate').click(function(){
            initFilter();
        });
    $node_filter.click(function(){
            if($node_filter.hasClass('init')){
                $node_filter.val('');
                $node_filter.removeClass('init');
            }
        });
    $node_filter.keyup(function(e){
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(updateFilter(e),600);
        });
};


var initCodeMirror = function(textarea_id, baseUrl, resetUrl){
    var myCodeMirror = CodeMirror.fromTextArea($('#' + textarea_id)[0], {
            mode: "null",
            lineNumbers: true,
            indentUnit: 4,
            autofocus: true
        });
    CodeMirror.modeURL = baseUrl + "/codemirror/mode/%N/%N.js";

    $('#reset').click(function(e){
            window.location=resetUrl;
        });

    $('#file_enable').click(function(){
            $('#editor_container').show();
            $('#upload_file_container').hide();
            $('#filename_container').show();
            $('#set_mode_header').show();
        });

    $('#upload_file_enable').click(function(){
            $('#editor_container').hide();
            $('#upload_file_container').show();
            $('#filename_container').hide();
            $('#set_mode_header').hide();
        });

    return myCodeMirror
};

var setCodeMirrorMode = function(codeMirrorInstance, mode) {
    CodeMirror.autoLoadMode(codeMirrorInstance, mode);
}


var _getIdentNode = function(n){
    //iterate thrugh nodes until matching interesting node

    if (typeof n == 'undefined'){
        return -1
    }

    if(typeof n.id != "undefined" && n.id.match('L[0-9]+')){
        return n
    }
    else{
        return _getIdentNode(n.parentNode);
    }
};

/* generate links for multi line selects that can be shown by files.html page_highlights.
 * This is a mouseup handler for hlcode from CodeHtmlFormatter and pygmentize */
var getSelectionLink = function(e) {
    //get selection from start/to nodes
    if (typeof window.getSelection != "undefined") {
        var s = window.getSelection();

        var from = _getIdentNode(s.anchorNode);
        var till = _getIdentNode(s.focusNode);

        var f_int = parseInt(from.id.replace('L',''));
        var t_int = parseInt(till.id.replace('L',''));

        var yoffset = 35;
        var ranges = [parseInt(from.id.replace('L','')), parseInt(till.id.replace('L',''))];
        if (ranges[0] > ranges[1]){
            //highlight from bottom
            yoffset = -yoffset;
            ranges = [ranges[1], ranges[0]];
        }
        var $hl_div = $('div#linktt');
        // if we select more than 2 lines
        if (ranges[0] != ranges[1]){
            if ($hl_div.length) {
                $hl_div.html('');
            } else {
                $hl_div = $('<div id="linktt" class="hl-tip-box">');
                $('body').prepend($hl_div);
            }

            $hl_div.append($('<a>').html(_TM['Selection Link']).prop('href', location.href.substring(0, location.href.indexOf('#')) + '#L' + ranges[0] + '-'+ranges[1]));
            var xy = $(till).offset();
            $hl_div.css('top', (xy.top + yoffset) + 'px').css('left', xy.left + 'px');
            $hl_div.show();
        }
        else{
            $hl_div.hide();
        }
    }
};

var deleteNotification = function(url, notification_id, callbacks){
    var success = function(o){
            $("#notification_"+notification_id).remove();
            _run_callbacks(callbacks);
        };
    var failure = function(o){
            alert("deleteNotification failure");
        };
    var postData = {'_method': 'delete'};
    var sUrl = url.replace('__NOTIFICATION_ID__',notification_id);
    ajaxPOST(sUrl, postData, success, failure);
};

var readNotification = function(url, notification_id, callbacks){
    var success = function(o){
            var $obj = $("#notification_"+notification_id);
            $obj.removeClass('unread');
            $obj.find('.read-notification').remove();
            _run_callbacks(callbacks);
        };
    var failure = function(o){
            alert("readNotification failure");
        };
    var postData = {'_method': 'put'};
    var sUrl = url.replace('__NOTIFICATION_ID__',notification_id);
    ajaxPOST(sUrl, postData, success, failure);
};

/**
 * Autocomplete functionality
 */

// Custom search function for the DataSource of users
var autocompleteMatchUsers = function (sQuery, myUsers) {
    // Case insensitive matching
    var query = sQuery.toLowerCase();
    var i = 0;
    var l = myUsers.length;
    var matches = [];

    // Match against each name of each contact
    for (; i < l; i++) {
        var contact = myUsers[i];
        if (((contact.fname+"").toLowerCase().indexOf(query) > -1) ||
             ((contact.lname+"").toLowerCase().indexOf(query) > -1) ||
             ((contact.nname) && ((contact.nname).toLowerCase().indexOf(query) > -1))) {
            matches[matches.length] = contact;
        }
    }
    return matches;
};

// Custom search function for the DataSource of userGroups
var autocompleteMatchGroups = function (sQuery, myGroups) {
    // Case insensitive matching
    var query = sQuery.toLowerCase();
    var i = 0;
    var l = myGroups.length;
    var matches = [];

    // Match against each name of each group
    for (; i < l; i++) {
        var matched_group = myGroups[i];
        if (matched_group.grname.toLowerCase().indexOf(query) > -1) {
            matches[matches.length] = matched_group;
        }
    }
    return matches;
};

// Helper highlight function for the formatter
var autocompleteHighlightMatch = function (full, snippet, matchindex) {
    return full.substring(0, matchindex)
        + "<span class='match'>"
        + full.substr(matchindex, snippet.length)
        + "</span>" + full.substring(matchindex + snippet.length);
};

var gravatar = function(link, size, cssclass) {
    var elem = '<img alt="" class="{2}" style="width: {0}px; height: {0}px" src="{1}"/>'.format(size, link, cssclass);
    if (!link) {
        elem = '<i class="icon-user {1}" style="font-size: {0}px;"></i>'.format(size, cssclass);
    }
    return elem;
}

var autocompleteGravatar = function(res, link, size, group) {
    var elem = gravatar(link, size, "perm-gravatar-ac");
    if (group !== undefined) {
        elem = '<i class="perm-gravatar-ac icon-users"></i>';
    }
    return '<div class="ac-container-wrap">{0}{1}</div>'.format(elem, res);
}

// Custom formatter to highlight the matching letters
var autocompleteFormatter = function (oResultData, sQuery, sResultMatch) {
    var query = sQuery.toLowerCase();

    // group
    if (oResultData.grname != undefined) {
        var grname = oResultData.grname;
        var grmembers = oResultData.grmembers;
        var grnameMatchIndex = grname.toLowerCase().indexOf(query);
        var grprefix = "{0}: ".format(_TM['Group']);
        var grsuffix = " ({0} {1})".format(grmembers, _TM['members']);

        if (grnameMatchIndex > -1) {
            return autocompleteGravatar(grprefix + autocompleteHighlightMatch(grname, query, grnameMatchIndex) + grsuffix, null, null, true);
        }
        return autocompleteGravatar(grprefix + oResultData.grname + grsuffix, null, null, true);

    // users
    } else if (oResultData.nname != undefined) {
        var fname = oResultData.fname || "";
        var lname = oResultData.lname || "";
        var nname = oResultData.nname;

        // Guard against null value
        var fnameMatchIndex = fname.toLowerCase().indexOf(query),
            lnameMatchIndex = lname.toLowerCase().indexOf(query),
            nnameMatchIndex = nname.toLowerCase().indexOf(query),
            displayfname, displaylname, displaynname, displayname;

        if (fnameMatchIndex > -1) {
            displayfname = autocompleteHighlightMatch(fname, query, fnameMatchIndex);
        } else {
            displayfname = fname;
        }

        if (lnameMatchIndex > -1) {
            displaylname = autocompleteHighlightMatch(lname, query, lnameMatchIndex);
        } else {
            displaylname = lname;
        }

        if (nnameMatchIndex > -1) {
            displaynname = autocompleteHighlightMatch(nname, query, nnameMatchIndex);
        } else {
            displaynname = nname;
        }

        displayname = displaynname;
        if (displayfname && displaylname) {
            displayname = "{0} {1} ({2})".format(displayfname, displaylname, displayname);
        }

        return autocompleteGravatar(displayname, oResultData.gravatar_lnk, oResultData.gravatar_size);
    } else {
        return '';
    }
};

// Generate a basic autocomplete instance that can be tweaked further by the caller
var autocompleteCreate = function ($inputElement, $container, matchFunc) {
    var datasource = new YAHOO.util.FunctionDataSource(matchFunc);

    var autocomplete = new YAHOO.widget.AutoComplete($inputElement[0], $container[0], datasource);
    autocomplete.useShadow = false;
    autocomplete.resultTypeList = false;
    autocomplete.animVert = false;
    autocomplete.animHoriz = false;
    autocomplete.animSpeed = 0.1;
    autocomplete.formatResult = autocompleteFormatter;

    return autocomplete;
}

var SimpleUserAutoComplete = function ($inputElement, $container, users_list) {

    var matchUsers = function (sQuery) {
        return autocompleteMatchUsers(sQuery, users_list);
    }

    var userAC = autocompleteCreate($inputElement, $container, matchUsers);

    // Handler for selection of an entry
    var itemSelectHandler = function (sType, aArgs) {
        var myAC = aArgs[0]; // reference back to the AC instance
        var elLI = aArgs[1]; // reference to the selected LI element
        var oData = aArgs[2]; // object literal of selected item's result data
        myAC.getInputEl().value = oData.nname;
    };
    userAC.itemSelectEvent.subscribe(itemSelectHandler);
}

var MembersAutoComplete = function ($inputElement, $container, users_list, groups_list) {

    var matchAll = function (sQuery) {
        var u = autocompleteMatchUsers(sQuery, users_list);
        var g = autocompleteMatchGroups(sQuery, groups_list);
        return u.concat(g);
    };

    var membersAC = autocompleteCreate($inputElement, $container, matchAll);

    // Handler for selection of an entry
    var itemSelectHandler = function (sType, aArgs) {
        var nextId = $inputElement.prop('id').split('perm_new_member_name_')[1];
        var myAC = aArgs[0]; // reference back to the AC instance
        var elLI = aArgs[1]; // reference to the selected LI element
        var oData = aArgs[2]; // object literal of selected item's result data
        //fill the autocomplete with value
        if (oData.nname != undefined) {
            //users
            myAC.getInputEl().value = oData.nname;
            $('#perm_new_member_type_'+nextId).val('user');
        } else {
            //groups
            myAC.getInputEl().value = oData.grname;
            $('#perm_new_member_type_'+nextId).val('users_group');
        }
    };
    membersAC.itemSelectEvent.subscribe(itemSelectHandler);
}

var MentionsAutoComplete = function ($inputElement, $container, users_list) {

    var matchUsers = function (sQuery) {
            var org_sQuery = sQuery;
            if(this.mentionQuery == null){
                return []
            }
            sQuery = this.mentionQuery;
            return autocompleteMatchUsers(sQuery, users_list);
    }

    var mentionsAC = autocompleteCreate($inputElement, $container, matchUsers);
    mentionsAC.suppressInputUpdate = true;
    // Overwrite formatResult to take into account mentionQuery
    mentionsAC.formatResult = function (oResultData, sQuery, sResultMatch) {
        var org_sQuery = sQuery;
        if (this.dataSource.mentionQuery != null) {
            sQuery = this.dataSource.mentionQuery;
        }
        return autocompleteFormatter(oResultData, sQuery, sResultMatch);
    }

    // Handler for selection of an entry
    if(mentionsAC.itemSelectEvent){
        mentionsAC.itemSelectEvent.subscribe(function (sType, aArgs) {
            var myAC = aArgs[0]; // reference back to the AC instance
            var elLI = aArgs[1]; // reference to the selected LI element
            var oData = aArgs[2]; // object literal of selected item's result data
            //Replace the mention name with replaced
            var re = new RegExp();
            var org = myAC.getInputEl().value;
            var chunks = myAC.dataSource.chunks
            // replace middle chunk(the search term) with actuall  match
            chunks[1] = chunks[1].replace('@'+myAC.dataSource.mentionQuery,
                                          '@'+oData.nname+' ');
            myAC.getInputEl().value = chunks.join('');
            myAC.getInputEl().focus(); // Y U NO WORK !?
        });
    }

    // in this keybuffer we will gather current value of search !
    // since we need to get this just when someone does `@` then we do the
    // search
    mentionsAC.dataSource.chunks = [];
    mentionsAC.dataSource.mentionQuery = null;

    mentionsAC.get_mention = function(msg, max_pos) {
        var org = msg;
        // Must match utils2.py MENTIONS_REGEX.
        // Only matching on string up to cursor, so it must end with $
        var re = new RegExp('(?:^|[^a-zA-Z0-9])@([a-zA-Z0-9][-_.a-zA-Z0-9]*[a-zA-Z0-9])$');
        var chunks  = [];

        // cut first chunk until current pos
        var to_max = msg.substr(0, max_pos);
        var at_pos = Math.max(0,to_max.lastIndexOf('@')-1);
        var msg2 = to_max.substr(at_pos);

        chunks.push(org.substr(0,at_pos)); // prefix chunk
        chunks.push(msg2);                 // search chunk
        chunks.push(org.substr(max_pos));  // postfix chunk

        // clean up msg2 for filtering and regex match
        var msg2 = msg2.lstrip(' ').lstrip('\n');

        if(re.test(msg2)){
            var unam = re.exec(msg2)[1];
            return [unam, chunks];
        }
        return [null, null];
    };

    $inputElement.keyup(function(e){
            var currentMessage = $inputElement.val();
            var currentCaretPosition = $inputElement[0].selectionStart;

            var unam = mentionsAC.get_mention(currentMessage, currentCaretPosition);
            var curr_search = null;
            if(unam[0]){
                curr_search = unam[0];
            }

            mentionsAC.dataSource.chunks = unam[1];
            mentionsAC.dataSource.mentionQuery = curr_search;
        });
}

var addReviewMember = function(id,fname,lname,nname,gravatar_link,gravatar_size){
    var displayname = nname;
    if ((fname != "") && (lname != "")) {
        displayname = "{0} {1} ({2})".format(fname, lname, nname);
    }
    var gravatarelm = gravatar(gravatar_link, gravatar_size, "");
    // WARNING: the HTML below is duplicate with
    // kallithea/templates/pullrequests/pullrequest_show.html
    // If you change something here it should be reflected in the template too.
    var element = (
        '     <li id="reviewer_{2}">\n'+
        '       <div class="reviewers_member">\n'+
        '           <div class="reviewer_status tooltip" title="not_reviewed">\n'+
        '             <i class="icon-circle changeset-status-not_reviewed"></i>\n'+
        '           </div>\n'+
        '         <div class="reviewer_gravatar gravatar">{0}</div>\n'+
        '         <div style="float:left;">{1}</div>\n'+
        '         <input type="hidden" value="{2}" name="review_members" />\n'+
        '         <div class="reviewer_member_remove action_button" onclick="removeReviewMember({2})">\n'+
        '             <i class="icon-minus-circled"></i>\n'+
        '         </div> (add not saved)\n'+
        '       </div>\n'+
        '     </li>\n'
        ).format(gravatarelm, displayname, id);
    // check if we don't have this ID already in
    var ids = [];
    $('#review_members').find('li').each(function() {
            ids.push(this.id);
        });
    if(ids.indexOf('reviewer_'+id) == -1){
        //only add if it's not there
        $('#review_members').append(element);
    }
}

var removeReviewMember = function(reviewer_id, repo_name, pull_request_id){
    var $li = $('#reviewer_{0}'.format(reviewer_id));
    $li.find('div div').css("text-decoration", "line-through");
    $li.find('input').prop('name', 'review_members_removed');
    $li.find('.reviewer_member_remove').replaceWith('&nbsp;(remove not saved)');
}

/* activate auto completion of users as PR reviewers */
var PullRequestAutoComplete = function ($inputElement, $container, users_list) {

    var matchUsers = function (sQuery) {
        return autocompleteMatchUsers(sQuery, users_list);
    };

    var reviewerAC = autocompleteCreate($inputElement, $container, matchUsers);
    reviewerAC.suppressInputUpdate = true;

    // Handler for selection of an entry
    if(reviewerAC.itemSelectEvent){
        reviewerAC.itemSelectEvent.subscribe(function (sType, aArgs) {
            var myAC = aArgs[0]; // reference back to the AC instance
            var elLI = aArgs[1]; // reference to the selected LI element
            var oData = aArgs[2]; // object literal of selected item's result data

            addReviewMember(oData.id, oData.fname, oData.lname, oData.nname,
                            oData.gravatar_lnk, oData.gravatar_size);
            myAC.getInputEl().value = '';
        });
    }
}

/**
 * Activate .quick_repo_menu
 */
var quick_repo_menu = function(){
    $(".quick_repo_menu").mouseenter(function(e) {
            var $menu = $(e.currentTarget).children().first().children().first();
            if($menu.hasClass('hidden')){
                $menu.removeClass('hidden').addClass('active');
                $(e.currentTarget).removeClass('hidden').addClass('active');
            }
        });
    $(".quick_repo_menu").mouseleave(function(e) {
            var $menu = $(e.currentTarget).children().first().children().first();
            if($menu.hasClass('active')){
                $menu.removeClass('active').addClass('hidden');
                $(e.currentTarget).removeClass('active').addClass('hidden');
            }
        });
};


/**
 * TABLE SORTING
 */

var revisionSort = function(a, b, desc, field) {
    var a_ = parseInt(a.getData('last_rev_raw') || 0);
    var b_ = parseInt(b.getData('last_rev_raw') || 0);

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var ageSort = function(a, b, desc, field) {
    // data is like: <span class="tooltip" date="2014-06-04 18:18:55.325474" title="Wed, 04 Jun 2014 18:18:55">1 day and 23 hours ago</span>
    var a_ = $(a.getData(field)).attr('date');
    var b_ = $(b.getData(field)).attr('date');

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var lastLoginSort = function(a, b, desc, field) {
    var a_ = parseFloat(a.getData('last_login_raw') || 0);
    var b_ = parseFloat(b.getData('last_login_raw') || 0);

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var nameSort = function(a, b, desc, field) {
    var a_ = a.getData('raw_name') || 0;
    var b_ = b.getData('raw_name') || 0;

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var dateSort = function(a, b, desc, field) {
    var a_ = parseFloat(a.getData('raw_date') || 0);
    var b_ = parseFloat(b.getData('raw_date') || 0);

    return YAHOO.util.Sort.compare(a_, b_, desc);
};

var addPermAction = function(_html, users_list, groups_list){
    var $last_node = $('.last_new_member').last(); // empty tr between last and add
    var next_id = $('.new_members').length;
    $last_node.before($('<tr class="new_members">').append(_html.format(next_id)));
    MembersAutoComplete($("#perm_new_member_name_"+next_id),
            $("#perm_container_"+next_id), users_list, groups_list);
}

function ajaxActionRevokePermission(url, obj_id, obj_type, field_id, extra_data) {
    var success = function (o) {
            $('#' + field_id).remove();
        };
    var failure = function (o) {
            alert(_TM['Failed to revoke permission'] + ": " + o.status);
        };
    var query_params = {
        '_method': 'delete'
    }
    // put extra data into POST
    if (extra_data !== undefined && (typeof extra_data === 'object')){
        for(var k in extra_data){
            query_params[k] = extra_data[k];
        }
    }

    if (obj_type=='user'){
        query_params['user_id'] = obj_id;
        query_params['obj_type'] = 'user';
    }
    else if (obj_type=='user_group'){
        query_params['user_group_id'] = obj_id;
        query_params['obj_type'] = 'user_group';
    }

    ajaxPOST(url, query_params, success, failure);
};

/* Multi selectors */

var MultiSelectWidget = function(selected_id, available_id, form_id){
    var $availableselect = $('#' + available_id);
    var $selectedselect = $('#' + selected_id);

    //fill available only with those not in selected
    var $selectedoptions = $selectedselect.children('option');
    $availableselect.children('option').filter(function(i, e){
            for(var j = 0, node; node = $selectedoptions[j]; j++){
                if(node.value == e.value){
                    return true;
                }
            }
            return false;
        }).remove();

    $('#add_element').click(function(e){
            $selectedselect.append($availableselect.children('option:selected'));
        });
    $('#remove_element').click(function(e){
            $availableselect.append($selectedselect.children('option:selected'));
        });

    $('#'+form_id).submit(function(){
            $selectedselect.children('option').each(function(i, e){
                e.selected = 'selected';
            });
        });
}

// custom paginator
var YUI_paginator = function(links_per_page, containers){

    (function () {

        var Paginator = YAHOO.widget.Paginator,
            l         = YAHOO.lang,
            setId     = YAHOO.util.Dom.generateId;

        Paginator.ui.MyFirstPageLink = function (p) {
            this.paginator = p;

            p.subscribe('recordOffsetChange',this.update,this,true);
            p.subscribe('rowsPerPageChange',this.update,this,true);
            p.subscribe('totalRecordsChange',this.update,this,true);
            p.subscribe('destroy',this.destroy,this,true);

            // TODO: make this work
            p.subscribe('firstPageLinkLabelChange',this.update,this,true);
            p.subscribe('firstPageLinkClassChange',this.update,this,true);
        };

        Paginator.ui.MyFirstPageLink.init = function (p) {
            p.setAttributeConfig('firstPageLinkLabel', {
                value : 1,
                validator : l.isString
            });
            p.setAttributeConfig('firstPageLinkClass', {
                value : 'yui-pg-first',
                validator : l.isString
            });
            p.setAttributeConfig('firstPageLinkTitle', {
                value : 'First Page',
                validator : l.isString
            });
        };

        // Instance members and methods
        Paginator.ui.MyFirstPageLink.prototype = {
            current   : null,
            leftmost_page: null,
            rightmost_page: null,
            link      : null,
            span      : null,
            dotdot    : null,
            getPos    : function(cur_page, max_page, items){
                var edge = parseInt(items / 2) + 1;
                if (cur_page <= edge){
                    var radius = Math.max(parseInt(items / 2), items - cur_page);
                }
                else if ((max_page - cur_page) < edge) {
                    var radius = (items - 1) - (max_page - cur_page);
                }
                else{
                    var radius = parseInt(items / 2);
                }

                var left = Math.max(1, (cur_page - (radius)));
                var right = Math.min(max_page, cur_page + (radius));
                return [left, cur_page, right]
            },
            render : function (id_base) {
                var p      = this.paginator,
                    c      = p.get('firstPageLinkClass'),
                    label  = p.get('firstPageLinkLabel'),
                    title  = p.get('firstPageLinkTitle');

                this.link     = document.createElement('a');
                this.span     = document.createElement('span');
                $(this.span).hide();

                var _pos = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                setId(this.link, id_base + '-first-link');
                this.link.href      = '#';
                this.link.className = c;
                this.link.innerHTML = label;
                this.link.title     = title;
                YUE.on(this.link,'click',this.onClick,this,true);

                setId(this.span, id_base + '-first-span');
                this.span.className = c;
                this.span.innerHTML = label;

                this.current = p.getCurrentPage() > 1 ? this.link : this.span;
                return this.current;
            },
            update : function (e) {
                var p      = this.paginator;
                var _pos   = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                if (e && e.prevValue === e.newValue) {
                    return;
                }

                var par = this.current ? this.current.parentNode : null;
                if (this.leftmost_page > 1) {
                    if (par && this.current === this.span) {
                        par.replaceChild(this.link,this.current);
                        this.current = this.link;
                    }
                } else {
                    if (par && this.current === this.link) {
                        par.replaceChild(this.span,this.current);
                        this.current = this.span;
                    }
                }
            },
            destroy : function () {
                YUE.purgeElement(this.link);
                this.current.parentNode.removeChild(this.current);
                this.link = this.span = null;
            },
            onClick : function (e) {
                YUE.stopEvent(e);
                this.paginator.setPage(1);
            }
        };

        })();

    (function () {

        var Paginator = YAHOO.widget.Paginator,
            l         = YAHOO.lang,
            setId     = YAHOO.util.Dom.generateId;

        Paginator.ui.MyLastPageLink = function (p) {
            this.paginator = p;

            p.subscribe('recordOffsetChange',this.update,this,true);
            p.subscribe('rowsPerPageChange',this.update,this,true);
            p.subscribe('totalRecordsChange',this.update,this,true);
            p.subscribe('destroy',this.destroy,this,true);

            // TODO: make this work
            p.subscribe('lastPageLinkLabelChange',this.update,this,true);
            p.subscribe('lastPageLinkClassChange', this.update,this,true);
        };

        Paginator.ui.MyLastPageLink.init = function (p) {
            p.setAttributeConfig('lastPageLinkLabel', {
                value : -1,
                validator : l.isString
            });
            p.setAttributeConfig('lastPageLinkClass', {
                value : 'yui-pg-last',
                validator : l.isString
            });
            p.setAttributeConfig('lastPageLinkTitle', {
                value : 'Last Page',
                validator : l.isString
            });

        };

        Paginator.ui.MyLastPageLink.prototype = {

            current   : null,
            leftmost_page: null,
            rightmost_page: null,
            link      : null,
            span      : null,
            dotdot    : null,
            na        : null,
            getPos    : function(cur_page, max_page, items){
                var edge = parseInt(items / 2) + 1;
                if (cur_page <= edge){
                    var radius = Math.max(parseInt(items / 2), items - cur_page);
                }
                else if ((max_page - cur_page) < edge) {
                    var radius = (items - 1) - (max_page - cur_page);
                }
                else{
                    var radius = parseInt(items / 2);
                }

                var left = Math.max(1, (cur_page - (radius)));
                var right = Math.min(max_page, cur_page + (radius));
                return [left, cur_page, right]
            },
            render : function (id_base) {
                var p      = this.paginator,
                    c      = p.get('lastPageLinkClass'),
                    label  = p.get('lastPageLinkLabel'),
                    last   = p.getTotalPages(),
                    title  = p.get('lastPageLinkTitle');

                var _pos = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                this.link = document.createElement('a');
                this.span = document.createElement('span');
                $(this.span).hide();

                this.na   = this.span.cloneNode(false);

                setId(this.link, id_base + '-last-link');
                this.link.href      = '#';
                this.link.className = c;
                this.link.innerHTML = label;
                this.link.title     = title;
                YUE.on(this.link,'click',this.onClick,this,true);

                setId(this.span, id_base + '-last-span');
                this.span.className = c;
                this.span.innerHTML = label;

                setId(this.na, id_base + '-last-na');

                if (this.rightmost_page < p.getTotalPages()){
                    this.current = this.link;
                }
                else{
                    this.current = this.span;
                }

                this.current.innerHTML = p.getTotalPages();
                return this.current;
            },

            update : function (e) {
                var p      = this.paginator;

                var _pos = this.getPos(p.getCurrentPage(), p.getTotalPages(), 5);
                this.leftmost_page = _pos[0];
                this.rightmost_page = _pos[2];

                if (e && e.prevValue === e.newValue) {
                    return;
                }

                var par   = this.current ? this.current.parentNode : null,
                    after = this.link;
                if (par) {

                    // only show the last page if the rightmost one is
                    // lower, so we don't have doubled entries at the end
                    if (!(this.rightmost_page < p.getTotalPages())){
                        after = this.span
                    }

                    if (this.current !== after) {
                        par.replaceChild(after,this.current);
                        this.current = after;
                    }
                }
                this.current.innerHTML = this.paginator.getTotalPages();

            },
            destroy : function () {
                YUE.purgeElement(this.link);
                this.current.parentNode.removeChild(this.current);
                this.link = this.span = null;
            },
            onClick : function (e) {
                YUE.stopEvent(e);
                this.paginator.setPage(this.paginator.getTotalPages());
            }
        };

        })();

    var pagi = new YAHOO.widget.Paginator({
        rowsPerPage: links_per_page,
        alwaysVisible: false,
        template : "{PreviousPageLink} {MyFirstPageLink} {PageLinks} {MyLastPageLink} {NextPageLink}",
        pageLinks: 5,
        containerClass: 'pagination-wh',
        currentPageClass: 'pager_curpage',
        pageLinkClass: 'pager_link',
        nextPageLinkLabel: '&gt;',
        previousPageLinkLabel: '&lt;',
        containers:containers
    });

    return pagi
}

var YUI_datatable = function(data, fields, columns, countnode, sortkey, rows){
    var myDataSource = new YAHOO.util.DataSource(data);
    myDataSource.responseType = YAHOO.util.DataSource.TYPE_JSON;
    myDataSource.responseSchema = {
        resultsList: "records",
        fields: fields
        };
    myDataSource.doBeforeCallback = function(req, raw, res, cb) {
        // This is the filter function
        var data     = res.results || [],
            filtered = [],
            i, l;

        if (req) {
            req = req.toLowerCase();
            for (i = 0; i<data.length; i++) {
                var pos = data[i].raw_name.toLowerCase().indexOf(req);
                if (pos != -1) {
                    filtered.push(data[i]);
                }
            }
            res.results = filtered;
        }
        $(countnode).html(res.results.length);
        return res;
    }

    var myDataTable = new YAHOO.widget.DataTable("datatable_list_wrap", columns, myDataSource, {
        sortedBy: {key:sortkey, dir:"asc"},
        paginator: YUI_paginator(rows !== undefined && rows ? rows : 25, ['user-paginator']),
        MSG_SORTASC: _TM['MSG_SORTASC'],
        MSG_SORTDESC: _TM['MSG_SORTDESC'],
        MSG_EMPTY: _TM['MSG_EMPTY'],
        MSG_ERROR: _TM['MSG_ERROR'],
        MSG_LOADING: _TM['MSG_LOADING']
        });
    myDataTable.subscribe('postRenderEvent',function(oArgs) {
        tooltip_activate();
        quick_repo_menu();
        });

    var filterTimeout = null;
    var $q_filter = $('#q_filter');

    var updateFilter = function () {
        // Reset timeout
        filterTimeout = null;

        // Reset sort
        var state = myDataTable.getState();
        state.sortedBy = {key:sortkey, dir:YAHOO.widget.DataTable.CLASS_ASC};

        // Get filtered data
        myDataSource.sendRequest($q_filter.val(), {
            success : myDataTable.onDataReturnInitializeTable,
            failure : myDataTable.onDataReturnInitializeTable,
            scope   : myDataTable,
            argument: state});
        };

    $q_filter.click(function(){
            if(!$q_filter.hasClass('loaded')){
                //TODO: load here full list later to do search within groups
                $q_filter.addClass('loaded');
            }
        });

    $q_filter.keyup(function (e) {
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(updateFilter, 600);
        });
}

/**
 Branch Sorting callback for select2, modifying the filtered result so prefix
 matches come before matches in the line.
 **/
var branchSort = function(results, container, query) {
    if (query.term) {
        return results.sort(function (a, b) {
            // Put closed branches after open ones (a bit of a hack ...)
            var aClosed = a.text.indexOf("(closed)") > -1,
                bClosed = b.text.indexOf("(closed)") > -1;
            if (aClosed && !bClosed) {
                return 1;
            }
            if (bClosed && !aClosed) {
                return -1;
            }

            // Put prefix matches before matches in the line
            var aPos = a.text.toLowerCase().indexOf(query.term.toLowerCase()),
                bPos = b.text.toLowerCase().indexOf(query.term.toLowerCase());
            if (aPos === 0 && bPos !== 0) {
                return -1;
            }
            if (bPos === 0 && aPos !== 0) {
                return 1;
            }

            // Default sorting
            if (a.text > b.text) {
                return 1;
            }
            if (a.text < b.text) {
                return -1;
            }
            return 0;
        });
    }
    return results;
};

var prefixFirstSort = function(results, container, query) {
    if (query.term) {
        return results.sort(function (a, b) {
            // if parent node, no sorting
            if (a.children != undefined || b.children != undefined) {
                return 0;
            }

            // Put prefix matches before matches in the line
            var aPos = a.text.toLowerCase().indexOf(query.term.toLowerCase()),
                bPos = b.text.toLowerCase().indexOf(query.term.toLowerCase());
            if (aPos === 0 && bPos !== 0) {
                return -1;
            }
            if (bPos === 0 && aPos !== 0) {
                return 1;
            }

            // Default sorting
            if (a.text > b.text) {
                return 1;
            }
            if (a.text < b.text) {
                return -1;
            }
            return 0;
        });
    }
    return results;
};

// global hooks after DOM is loaded

$(document).ready(function(){
    $('.diff-collapse-button').click(function(e) {
        var $button = $(e.currentTarget);
        var $target = $('#' + $button.prop('target'));
        if($target.hasClass('hidden')){
            $target.removeClass('hidden');
            $button.html("&uarr; {0} &uarr;".format(_TM['Collapse Diff']));
        }
        else if(!$target.hasClass('hidden')){
            $target.addClass('hidden');
            $button.html("&darr; {0} &darr;".format(_TM['Expand Diff']));
        }
    });
});
