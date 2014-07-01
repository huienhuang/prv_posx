

function go_home()
{
    var pn = window.location.pathname;
    var idx = pn.lastIndexOf('/');
    if (idx < 0) return;
    window.location = pn.substring(0, idx) + '/home';
}

function str_pad(s, n, f)
{
    f = f[0];
    for(var i = ('' + s).length; i < n; i++) s = f + s;
    return s;
}

function fmt_date(ts)
{
    var t = new Date();
    if(ts !== undefined) t.setTime(ts * 1000);
    
    var month = t.getMonth() + 1
    var day = t.getDate();
    var year = t.getFullYear();
    
    return str_pad(month, 2, '0') + '/' + str_pad(day, 2, '0') + '/' + year;
}

function fmt_time(ts)
{
    var t = new Date();
    if(ts !== undefined) t.setTime(ts * 1000);
    return fmt_time_by_date(t);
}

function fmt_time_by_date(t)
{
    var month = t.getMonth() + 1
    var day = t.getDate();
    var year = t.getFullYear();
    
    var hour = t.getHours();
    var minute = t.getMinutes();
    var second = t.getSeconds();
    
    var n = ' AM';
    if(hour >= 12) {
        hour -= 12;
        n = ' PM';
    }
    if(hour == 0) hour = 12;
    
    return str_pad(month, 2, '0') + '/' + str_pad(day, 2, '0') + '/' + year
            + ' ' + str_pad(hour, 2, '0') + ':' + str_pad(minute, 2, '0') + ':' + str_pad(second, 2, '0') + n;
}

function open_printing_wnd__delivery(d_id, tmpl)
{
    window.open('receipt?fn=delivery_printing_'+tmpl+'&d_id='+d_id,'posx_printing_wnd__delivery','location=0,width=992,height=700');
}

function idx_elements(blk, nz_prefix_len)
{
    var in_els = {}
    var lst = blk.find('input,select,textarea');
    for(var y = 0; y < lst.length; y++) {
        var o = $(lst[y]);
        var a = {};
        if( o.prop("tagName").toLowerCase() === 'select' ) {
            var l = o.children('option');
            for(var i = 0; i < l.length; i++) {
                var d = $(l[i]);
                var k = parseInt(d.val());
                a[k] = d.html();
            }
        }
        in_els[ o.attr('name').substr(nz_prefix_len) ] = [o, a];
    }
    
    blk.data('in_els', in_els);
}



(function() {


if(window.__js_posx_inited) return;
window.__js_posx_inited = true;
    

var v_msgbox = null;

function msg_box(title, msg, msg_type, cb)
{
    if(msg_type)
        v_msgbox.html(msg).dialog('option', 'title', title).dialog('open');
    else
        v_msgbox.empty().append($('<pre></pre>').text(msg)).dialog('option', 'title', title).dialog('open');
}

MsgBox = function(title, msg, msg_type, cb)
{
    if (!v_msgbox) {
        v_msgbox = $('<div id="__dlg_msgbox"></div>')
        .appendTo($('body'))
        .dialog({
            modal:true,
            autoOpen:false,
            close: function(event, ui) {
                var mq = $(this).data('mq');
                var cb = mq.shift()[3];
                if (cb !== undefined) {
                    if (cb.type === 0) cb.func.apply(cb.this || window, cb.args || []);
                    if (cb.type === 1) window.location = '?';
                    if (cb.type === 2) window.close();
                }
                if(mq[0] !== undefined) msg_box.apply(this, mq[0]);
            }
        }).data('mq', []);
    }
    
    var mq = v_msgbox.data('mq');
    mq.push( [title, msg, msg_type, cb] );
    if(v_msgbox.dialog('isOpen')) return;
    msg_box.apply(this, mq[0]);
};



var timeout_chk_login = null;
var v_login = null;

function load_users()
{
    if(!v_login) return;
        
    $.get('?fn=getusers', {}, function(js) {
        var els = v_login.data('in_els');
        var v_uid = els.uid[0].empty();
        v_uid.append('<option value="0"> -- Select -- </option>')
        for(var i = 0; i < js.length; i++) v_uid.append( $('<option></option>').text(js[i][1]).val(js[i][0]) );
            
    }, 'json');
        
}
    
function login()
{
    var els = v_login.data('in_els');
    var user_id = parseInt(els.uid[0].val());
    var user_passwd = $.trim(els.pass[0].val());
    els.pass[0].val('');
    if(!user_id || !user_passwd) return;
        
    $.post('?fn=login_js', {'user_id':user_id, 'user_passwd':user_passwd}, function(js) {
        if(!js || !js.user_id) return;
        v_login.dialog('close');
    }, 'json');
        
}
    
function show_login()
{
    if(v_login && v_login.dialog('isOpen') ) return;
        
    if(!v_login) {
        v_login = $('<div id="__g_v_login" title="Log In" style="line-height:36px;text-align:center"><div><select name="uid" style="width:200px" /></select></div><div><input type="password" name="pass" placeholder="password" style="width:194px" /></div></div>')
        .appendTo($('body'))
        .dialog({
            modal:true,
            autoOpen:false,
            width:300,
            close: function() { v_login.data('in_els').pass[0].val(''); },
            buttons: {'login': login}
        });
        idx_elements(v_login, 0);
        v_login.data('in_els').pass[0].keyup(function(e) { e.which === 13 && login(); });
    }
    
    load_users();
    v_login.dialog('open');
}


function chk_login()
{
    $.get('?fn=getuser', {}, function(js) {
        if(!js || js.user_id !== 0) {
            v_login && v_login.dialog('close');
        } else {
            show_login();
        }
            
        timeout_chk_login && clearTimeout(timeout_chk_login);
        timeout_chk_login = setTimeout(chk_login, 5000);
            
    }, 'json').error(function() {
        v_login && v_login.dialog('close');
            
        timeout_chk_login && clearTimeout(timeout_chk_login);
        timeout_chk_login = setTimeout(chk_login, 5000);
    });
}
    
if(window.posx_enable_chk_login) timeout_chk_login = setTimeout(chk_login, 5000);




function itemsearch_render_item(ul, item)
{
    var d = item[3];
    
    var unit = d.units[d.default_uom_idx];
    var qty = unit[3] ? Math.floor(unit[3] != 1 ? d.qty[0] / unit[3] : d.qty[0]) : 'E';
    return $('<li class="srch_item"></li>').append(
        $('<a></a>')
            .append($('<span></span>').text(item[1]))
            .append($('<span></span>').text(d.units[0][1]))
            .append($('<span></span>').text( '$' + unit[0][0] + (unit[2] ? '/' + unit[2] : '') + ' (' + qty +')' ))
            .append($('<span></span>').text(item[2]))
    ).appendTo(ul);
    
}

function ac_item_search_response(event, ui) {
    var ct = ui.content;
    var term = $.trim( $(this).data("ui-autocomplete").term.toLowerCase() );
        
    for(var i = 0; i < ct.length; i++) {
        var c = ct[i];
        if(typeof(c[3]) === typeof("")) c[3] = $.parseJSON(c[3]);
        var item = c[3];
        var units = item.units;
            
        if (c[4] !== null) {
            var upc_uom_idx = parseInt(c[4]);
            if(upc_uom_idx >= 0 && upc_uom_idx < units.length) item.default_uom_idx = upc_uom_idx;
                
        } else if(term) {
            for(var u = 0; u < units.length; u++) {
                var alu = units[u][1];
                if(alu && alu.toLowerCase() === term) {
                    item.default_uom_idx = u;
                    break;
                }
            }
        }

    }
}

init_item_ac = function(sel, cb, option, fn_render)
{
    var ac = $(sel).autocomplete( $.extend({
        autoFocus: true,
        source: "sync?fn=itemsearch",
        minLength: 1,
        select: cb,
        response: ac_item_search_response,
    }, option) );
    ac.data("ui-autocomplete")._renderItem = fn_render || itemsearch_render_item;
    
    return ac;
};


var v_loading_msg = null;
function show_loading_msg(msg)
{
    if(!v_loading_msg) { v_loading_msg = $('<div class="center_blk" style="display:none;z-index:99"></div>').appendTo($('body')); }
    
    v_loading_msg.text(msg).stop(true, true).show();
}

function hide_loading_msg()
{
    v_loading_msg && v_loading_msg.fadeOut(1000);
}

load_js = function(type, msg, url, data, cb, err_cb, sync)
{
    msg && show_loading_msg(msg);
    return $.ajax({
        async: !sync,
        type: type,
        url: url,
        data: data,
        success: function() {
            hide_loading_msg();
            cb && cb.apply(this, arguments);
        },
        dataType: 'json',
        error: function() {
            hide_loading_msg();
            if(err_cb)
                err_cb.apply(this, arguments);
            else
                MsgBox('Erorr', 'unexpected error');
        }
    });
};

var load_js_ex__s_tag = {}
load_js_ex = function(type, msg, url, data, cb, err_cb, sync, s_tag)
{
    var cur_seq = 0;
    if(s_tag) cur_seq = load_js_ex__s_tag[s_tag] = load_js_ex__s_tag[s_tag] ? load_js_ex__s_tag[s_tag] + 1 : 1;
    
    msg && show_loading_msg(msg);
    return $.ajax({
        async: !sync,
        type: type,
        url: url,
        data: data,
        success: function(js) {
            if(s_tag && load_js_ex__s_tag[s_tag] !== cur_seq) return;
            
            hide_loading_msg();
            if(js.err) {
                if(js.err === -999) {
                    show_login();
                } else if(err_cb)
                    err_cb.call(this, 1, arguments);
                else
                    MsgBox('Erorr Code - ' + (js.err || 'None'), js.err_s || 'unexpected error');
            } else
                cb && cb.apply(this, arguments);
        },
        dataType: 'json',
        error: function() {
            if(s_tag && load_js_ex__s_tag[s_tag] !== cur_seq) return;
            
            hide_loading_msg();
            if(err_cb)
                err_cb.call(this, 0, arguments);
            else
                MsgBox('Erorr', 'unexpected error');
        }
    });
};

post_js = function(url, data, cb, err_cb, sync)
{
    return load_js('post', 'Saving...', url, data, cb, err_cb, sync);
};

get_js = function(url, data, cb, err_cb, sync)
{
    return load_js('get', null, url, data, cb, err_cb, sync);
};

post_js_ex = function(url, data, cb, err_cb, sync, pop_msg, s_tag)
{
    return load_js_ex('post', pop_msg !== undefined ? pop_msg : 'Saving...', url, data, cb, err_cb, sync, s_tag);
};

get_js_ex = function(url, data, cb, err_cb, sync, pop_msg, s_tag)
{
    return load_js_ex('get', pop_msg, url, data, cb, err_cb, sync, s_tag);
};

})();

