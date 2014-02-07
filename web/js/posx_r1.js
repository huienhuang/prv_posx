//2013-06-26


var __g_v_msgbox = null;

function _MsgBox(title, msg, msg_type, cb)
{
    if(msg_type)
        __g_v_msgbox.html(msg).dialog('option', 'title', title).dialog('open');
    else
        __g_v_msgbox.empty().append($('<pre></pre>').text(msg)).dialog('option', 'title', title).dialog('open');
}

function MsgBox(title, msg, msg_type, cb)
{
    if (!__g_v_msgbox) {
        __g_v_msgbox = $('<div id="__dlg_msgbox"></div>')
        .appendTo($('body'))
        .dialog({
            modal:true,
            autoOpen:false,
            width:700,
            close: function(event, ui) {
                var mq = $(this).data('mq');
                var cb = mq.shift()[3];
                if (cb !== undefined) {
                    if (cb.type === 0) cb.func.apply(cb.this || window, cb.args || []);
                    if (cb.type === 1) window.location = '?';
                    if (cb.type === 2) window.close();
                }
                if(mq[0] !== undefined) _MsgBox.apply(this, mq[0]);
            }
        }).data('mq', []);
    }
    
    var mq = __g_v_msgbox.data('mq');
    mq.push( [title, msg, msg_type, cb] );
    if(__g_v_msgbox.dialog('isOpen')) return;
    _MsgBox.apply(this, mq[0]);
}

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


var __timeout_chk_login = null;
var __g_v_login = null;
(function() {
    
    function load_users()
    {
        if(!__g_v_login) return;
        
        $.get('?fn=getusers', {}, function(js) {
            var els = __g_v_login.data('in_els');
            var v_uid = els.uid[0].empty();
            v_uid.append('<option value="0"> -- Select -- </option>')
            for(var i = 0; i < js.length; i++) v_uid.append( $('<option></option>').text(js[i][1]).val(js[i][0]) );
            
        }, 'json');
        
    }
    
    function login()
    {
        var els = __g_v_login.data('in_els');
        var user_id = parseInt(els.uid[0].val());
        var user_passwd = $.trim(els.pass[0].val());
        els.pass[0].val('');
        if(!user_id || !user_passwd) return;
        
        $.post('?fn=login_js', {'user_id':user_id, 'user_passwd':user_passwd}, function(js) {
            if(!js || !js.user_id) return;
            __g_v_login.dialog('close');
        }, 'json');
        
    }
    
    function show_login()
    {
        if(__g_v_login && __g_v_login.dialog('isOpen') ) return;
        
        if(!__g_v_login) {
            __g_v_login = $('<div id="__g_v_login" title="Log In" style="line-height:36px;text-align:center"><div><select name="uid" style="width:200px" /></select></div><div><input type="password" name="pass" placeholder="password" style="width:194px" /></div></div>')
            .appendTo($('body'))
            .dialog({
                modal:true,
                autoOpen:false,
                width:300,
                buttons: {
                    'login': login
                }
            });
            idx_elements(__g_v_login, 0);
        }
        
        load_users();
        __g_v_login.dialog('open');
    }
    
    
    function chk_login()
    {
        $.get('?fn=getuser', {}, function(js) {
            if(!js || js.user_id !== 0) {
                __g_v_login && __g_v_login.dialog('close');
            } else {
                show_login();
            }
            
            __timeout_chk_login && clearTimeout(__timeout_chk_login);
            __timeout_chk_login = setTimeout(chk_login, 5000);
            
        }, 'json').error(function() {
            __g_v_login && __g_v_login.dialog('close');
            
            __timeout_chk_login && clearTimeout(__timeout_chk_login);
            __timeout_chk_login = setTimeout(chk_login, 5000);
        });
    }
    
    __timeout_chk_login = setTimeout(chk_login, 5000);
    
})();

