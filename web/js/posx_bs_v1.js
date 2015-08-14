

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
    var pjs = v_msgbox.data('pjs');
    
    if(msg_type)
        pjs.v_body.html(msg);
    else
        pjs.v_body.empty().append($('<div style="white-space:pre-wrap"></div>').text(msg));
    
    pjs.v_title.text(title);
    v_msgbox.modal('show');
}

MsgBox = function(title, msg, msg_type, cb)
{
    if (!v_msgbox) {
        v_msgbox = $('<div class="modal fade" role="dialog"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button><h4 class="modal-title"></h4></div><div class="modal-body"></div></div></div></div>')
        .appendTo($('body')).modal({show: false})
        .on('hidden.bs.modal', function(e) {
            var mq = $(this).data('pjs').mq;
            var cb = mq.shift()[3];
            if (cb !== undefined) {
                if (cb.type === 0) cb.func.apply(cb.this || window, cb.args || []);
                if (cb.type === 1) window.location = '?';
                if (cb.type === 2) window.close();
                }
            if(mq[0] !== undefined) msg_box.apply(this, mq[0]);
        });
        
        v_msgbox.data('pjs', {'mq': [], 'v_title': v_msgbox.find('.modal-title'), 'v_body': v_msgbox.find('.modal-body')});
    }
    
    var mq = v_msgbox.data('pjs').mq;
    mq.push( [title, msg, msg_type, cb] );
    if(v_msgbox.is(':visible')) return;
    msg_box.apply(this, mq[0]);
};

var v_loading_msg = null;
function show_loading_msg(msg)
{
    if(!v_loading_msg) { v_loading_msg = $('<div class="center_blk" style="display:none;z-index:9999"></div>').appendTo($('body')); }
    
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
                    MsgBox('Erorr Code #' + (js.err || 'None'), js.err_s || 'unexpected error');
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


var __c_wnds = {};
open_wnd = function(url, nz, width, height) {
    __c_wnds[nz] && __c_wnds[nz].window && __c_wnds[nz].close && __c_wnds[nz].close();
    __c_wnds[nz] = window.open(url, nz, 'location=0,width='+(width || 992)+',height='+(height || 700));
};

})();

