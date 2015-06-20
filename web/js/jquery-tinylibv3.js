//v3 - 09/06/2013 - simplify ajax response
//v2 - 06/29/2013 - always show scroll-y


(function($) {


var g_tg_ctrl = {
    
'image': {
    type: 0, //one widget per cell
    init: function() {
        return this.append('<image alt="" class="tg_col_c_image" />').children('.tg_col_c_image').data('tg_image_timer', {v:null});
    },
    set: function(co, val) {
        var timer = co.data('tg_image_timer');
        if(timer.v !== null) { clearTimeout(timer.v); timer.v = null; }
        co.hide();
        if(val !== null) timer.v = setTimeout( function() { timer.v = null; co.attr('src', val).show(); }, 300 );
    }
},

'edit': {
    type: 1, //only one widget for cells
    init: function() {
        return this.append('<input type="text" class="tg_col_c_text" />').children('.tg_col_c_text');
    },
    click: function(co, row, cidx, ctx) {
        co.width(this.width()).height(this.height()).css('top', row[0].css('top')).css('left', this.position().left).val(row[4][cidx]).focus();
    },
    focusout: function(co, row, cidx, oval, ctx) {
        var nval = $.trim(co.val());
        if(nval === oval[cidx]) return;
        if(ctx.ctrl_change && ctx.ctrl_change.apply(ctx, [row[1], cidx, oval[cidx], nval, ctx.cols[cidx].fieldname, oval]) === false) return;
        row[4][cidx] = nval;
        this.text(nval);
    }
},

'select': {
    type: 1,
    init: function() {
        return this.append('<select class="tg_col_c_select"></select>').children('.tg_col_c_select');
    },
    click: function(co, row, cidx, ctx) {
        var ed = row[4][cidx];
        var optd = ed[1];
        var opte = co.children('option');
        
        if(opte.length < optd.length) {
            var s = '';
            for(var i = opte.length; i < optd.length; i++) s += '<option></option>';
            opte = co.append(s).children('option');
        }
        
        if(ed[2]) {
            for(var i = 0; i < optd.length; i++) $(opte[i]).val(optd[i][0]).text(optd[i][1]).show();
        } else {
            for(var i = 0; i < optd.length; i++) $(opte[i]).val(optd[i]).text(optd[i]).show();
        }
        
        opte.slice(optd.length).filter(':visible').val('').text('').hide();
        
        co.width(this.width()).height(this.height()).css('top', row[0].css('top')).css('left', this.position().left).val(ed[0]).focus();
    },
    set: function(co, val) {
        this.text(val ? val[0] : '');
    },
    focusout: function(co, row, cidx, oval, ctx) {
        var nval = $.trim(co.val());
        if(nval === oval[cidx][0]) return;
        if(ctx.ctrl_change && ctx.ctrl_change.apply(ctx, [row[1], cidx, oval[cidx][0], nval, ctx.cols[cidx].fieldname, oval]) === false) return;
        row[4][cidx][0] = nval;
        this.text(nval);
    }
},

};


function init(a) {
    var ctx = {
        src: null,
        cols: [],
        len:0,
        sortby:[0, 0],
        init:null,
        click: null,
        select: null,
        change: null,
        render: null,
        getval: null,
        ctrl_change: null,
        ctrls: {},
        cache_change: null,
        footer_html: '<div class="tgft_page"></div>',
        auto_resize: true,
        load_delay: 100,
    };
    $.extend(ctx, a);
    ctx.view = {
        seq:0, len:-1, from:-1, to:-1, sortby:[ctx.sortby[0], ctx.sortby[1]], dataseq:0,
        buf:{
            pagesize:0,
            maxpage:ctx.src && ctx.src.maxpage ? ctx.src.maxpage : 3,
            pagesize_mul:ctx.src && ctx.src.pagesize_mul ? ctx.src.pagesize_mul : 2,
            }
    };
    
    var s;
    s = '<div class="tg_header"></div><div class="tg_body"><div class="tg_meter"></div><div class="tg_table"><div class="tg_row"></div></div></div><div class="tg_footer">'+ctx.footer_html+'</div>';
    this.addClass('tinygrid').html(s);
    var tg_header = this.children('.tg_header');
    var tg_body = this.children('.tg_body');
    var tg_cont = tg_body.children('.tg_table');
    var tg_meter = tg_body.children('.tg_meter');
    var tg_footer = this.children('.tg_footer');
    var row_height = tg_cont.children('.tg_row').outerHeight(false);
    tg_cont.empty();
    
    var tg_ctrl = {};
    var ctrls = $.extend({}, g_tg_ctrl, ctx.ctrls);
    for(var i in ctrls) {
        var j = ctrls[i];
        if(!j || j.type != 1) continue;
        var ct = j.init.call(tg_cont);
        if(j.focusout) ct.focusout(ctrl_focusout).keyup(ctrl_keyup);
        var ct_d = [ct, -1, 0, null];
        ct.data('tinygrid_ctrl', {d:ct_d, ctx:ctx});
        tg_ctrl[i] = ct_d;
    }
    
    var aw = 0;
    var h = '';
    var cm = '';
    var tw = 0;
    var cols = ctx.cols;
    for(var i = 0; i < cols.length; i++) {
        var n = cols[i];
        var w = n.width;
        if(!aw && typeof w == 'string' && w.indexOf('%') >= 0) aw = 1;
        w = parseInt(w);
        h += '<div class="tg_col" style="width:'+w+'px;">'+n.name+'</div>';
        cm += '<div class="tg_col" style="width:'+w+'px;"></div>';
        tw += w + 1;
    }
    
    tg_cont.width(tw);
    var eh = tg_header.width(tw).html(h).children('.tg_col').click(header_col_click);
    var header_row = [];
    for(var i = 0; i < eh.length; i++) {
        var ec = $(eh[i]);
        ec.data('tinygrid_col_hdr', {c:i, ctx:ctx});
        header_row[i] = ec;
    }
    header_row[ ctx.sortby[0] ].addClass(ctx.sortby[1] ? 'tg_col_sort_desc' : 'tg_col_sort_asc');
    
    var footer_row = {};
    var ef = tg_footer.children('div');
    for(var i = 0; i < ef.length; i++) {
        var ec = $(ef[i]);
        var cls = ec.attr('class');
        var idx = cls.indexOf('tgft_');
        if(idx < 0) continue;
        footer_row[ cls.split(' ')[0].substr(idx + 5) ] = ec;
    }
    
    ctx.data = {
        height:null,
        width:null,
        numrows:null,
        row_height:row_height,
        rows:[],
        tg:this,
        body:tg_body,
        header:tg_header,
        header_row:header_row,
        footer:tg_footer,
        footer_row:footer_row,
        cont:tg_cont,
        meter:tg_meter,
        left:-1,
        ctrl:tg_ctrl,
        col_html:cm,
        col_autowidth:aw,
        pagesize:null,
        select_data:[-1, false, false],
        reqs:[0, null],
        lockview:0,
        need_render:false,
        load_data_timer:null,
        resizer: function() { update.apply(ctx, [-1, true, false, false, true]); }
        };
    
    ctx.init && ctx.init.call(ctx);
    
    this.data('tinygrid', ctx);
    tg_body.data('tinygrid', ctx).scroll(i_scroll);
    
    update.apply(ctx, [ctx.len, true]);
    
    if(ctx.auto_resize) $(window).resize(ctx.data.resizer);
}

function remove()
{
    var ctx = this;
    var data = ctx.data;
    var view = ctx.view;
    var reqs = data.reqs;
    
    if(reqs[0] && reqs[1]) reqs[1].abort();
    reqs[0]++;
    reqs[1] = null;
    
    $(window).off('resize', ctx.data.resizer);
    
    ctx.data = null;
    
    data.tg.data('tinygrid', null);
    data.tg.remove();
}

function autowidth(ctx)
{
    var view = ctx.view;
    var data = ctx.data;
    var cols = ctx.cols;
    var clsz = cols.length;
    var cw = data.width - clsz;
    var ps = 0;

    var ws = [];
    var lc = -1;
    for(var i = 0; i < clsz; i++) {
        var w = cols[i].width;
        var a = [0, parseInt(w)];
        
        if(typeof w == 'string' && w.indexOf('%')) {
            a[0] = 1;
            ps += a[1];
            lc = i;
        } else
            cw -= a[1];
        
        ws[i] = a;
    }
    
    if(cw <= 0 || ps <= 0) return;
    
    var tw = 0;
    var c = '';
    var rcw = cw;
    for(var i = 0; i < clsz; i++) {
        var a = ws[i];
        if(a[0]) {
            a[1] = ( i == lc ? rcw : Math.floor(a[1] / ps * cw) );
            rcw -= a[1];
        }
        tw += a[1] + 1;
        c += '<div class="tg_col" style="width:'+a[1]+'px;"></div>';
    }
    
    var b = data.body;
    b.unbind('scroll');
    data.cont.width(tw);
    data.header.width(tw);
    b.scroll(i_scroll);
    
    var rows = data.rows;
    var rlen = rows.length;
    for(var r = 0; r < rlen; r++) {
        var cc = rows[r][3];
        for(var i = 0; i < clsz; i++) {
            var a = ws[i];
            if(a[0]) cc[i][0].width(a[1]);
        }
    }
    
    var row = data.header_row;
    for(var i = 0; i < clsz; i++) {
        var a = ws[i];
        if(a[0]) row[i].width(a[1]);
    }
    
    data.col_html = c;
    
}

function buf_getval(r)
{
    var buf = this.view.buf;
    var psz = buf.pagesize;
    var pgs = buf.pages;
    if(!psz) return null;
    var p = pgs[ Math.floor(r / psz) ];
    if(p) return p[ r % psz ];
    return null;
}

function emb_getval(r)
{
    return this.src.page[r];
}

function getval(r)
{
    if(this.getval)
        return this.getval.apply(this, [r, typeof(this.src.page) == 'string' ? buf_getval : emb_getval]);
    else if(typeof(this.src.page) == 'string')
        return buf_getval.apply(this, [r]);
    else
        return emb_getval.apply(this, [r]);
}

function header_col_click()
{
    var e = $(this);
    var d = e.data('tinygrid_col_hdr');
    var ctx = d.ctx;
    if(!ctx.cols[d.c].sortable) {
        update.apply(ctx, [-1, true, [-1], true]);
        return false;
    }
    
    var sb = ctx.view.sortby;
    var hdr_row = ctx.data.header_row;
    
    if(sb[0] >= 0) {
        hdr_row[ sb[0] ].removeClass(sb[1] ? 'tg_col_sort_desc' : 'tg_col_sort_asc');
    }
    
    sb[1] = sb[0] == d.c ? Number(!sb[1]) : 0;
    sb[0] = d.c;
    
    hdr_row[ sb[0] ].addClass(sb[1] ? 'tg_col_sort_desc' : 'tg_col_sort_asc');
    
    if(!ctx.sort || ctx.sort.call(ctx) !== false)
        update.apply(ctx, [-1, true, [-1], true]);
    
    return false;
}

function pop_rows(ctx)
{
    var data = ctx.data;
    var numrows = Math.ceil( data.height / data.row_height ) + 1;
    
    data.numrows = numrows;
    data.pagesize = numrows * ctx.view.buf.pagesize_mul;
    
    var n_rowlen = numrows * 2;
    var rows = data.rows;
    var o_rowlen = rows.length;
    if(n_rowlen <= o_rowlen) return;
    
    var c = data.col_html;
    var s = '';
    n_rowlen *= 2;
    for(var i = o_rowlen; i < n_rowlen; i++)
        s += '<div class="tg_row">' + c + '</div>';
    
    var cols = ctx.cols;
    var cols_len = cols.length;
    var ctrl = data.ctrl;
    var gctrl = $.extend({}, g_tg_ctrl, ctx.ctrls);
    var erows = data.cont.append(s).find('> div.tg_row');
    for(var i = o_rowlen; i < n_rowlen; i++) {
        var e = $(erows[i]);
        var ce = e.find('> div.tg_col').click(col_click);
        var cc = [];
        for(var j = 0; j < cols_len; j++) {
            var co = $(ce[j]).data('tinygrid_col', {r:i, c:j, ctx:ctx});
            var cd = cols[j];
            if(cd.hover) co.hover(col_hover_in, col_hover_out);
            var ct = cd.ctrlname;
            var cf = ct && gctrl[ct] ? gctrl[ct] : null;
            var ch = null;
            if(cf) {
                if(cf.type == 1) ch = ctrl[ct];
                else if(!cf.type) ch = [cf.init.call(co)];
            }
            cc[j] = [ co, cf, ch ];
        }
        rows[i] = [e, -1, -1, cc, null];
    }
    
}

function i_scroll()
{
    var ctx = $(this).data('tinygrid');
    var data = ctx.data;
    var left = data.body.scrollLeft();
    if(data.left != left) {
        data.left = left;
        data.header.css('left', -left);
    }
    update.apply(ctx, [-1, true]);
}

function change(force_render, dont_load_data)
{
    var ctx = this;
    var data = ctx.data;
    var view = ctx.view;
    
    var width = data.meter.width();
    if(data.width != width) {
        data.width = width;
        if(data.col_autowidth) autowidth(ctx);
    }
    
    var height = data.body.height();
    if(data.height != height) {
        data.height = height;
        pop_rows(ctx);
        force_render = true;
    }
    
    var top = data.body.scrollTop();
    var from = Math.floor(top / data.row_height);
    var to = Math.min(Math.ceil((top + data.height) / data.row_height), view.len);
    if(from != view.from || to != view.to) {
        view.from = from;
        view.to = to;
        if(ctx.change) ctx.change.call(ctx);
        render.call(ctx);
        
    } else if(force_render) {
        render.call(ctx);
        
    }
    
    if(!dont_load_data) {
        if(data.load_data_timer !== null) { clearTimeout(data.load_data_timer); data.load_data_timer = null; }
        data.load_data_timer = setTimeout( function() { data.load_data_timer = null; load_data.call(ctx); }, ctx.load_delay );
    }
    if(data.select_data[0] >= 0) select.apply(ctx, [data.select_data[0]]);
}

function ajax_on_error(req)
{
    var ctx = this.data('tinygrid');
    var reqs = ctx.data.reqs;
    reqs[0]--; reqs[1] = null;
    console.log('ajax_on_error');
}

function load_data_cb(jsn, status, req)
{
    var ctx = this.data('tinygrid');
    var data = ctx.data;
    var reqs = data.reqs;
    reqs[0]--; reqs[1] = null;
    if(!jsn || !jsn.res) return;
    var len = jsn.res.len;
    var view = ctx.view;
    var buf = view.buf;
    if(jsn.res.dataseq != view.dataseq) {
        view.dataseq = jsn.res.dataseq;
        buf.cachelist = [];
        buf.pages = {};
    }
    if(!len && !view.len) return;
    
    var cl = buf.cachelist;
    var pg = buf.pages;
    var sidx = data.req_pg[0];
    var max_pg = Math.ceil(len / buf.pagesize);
    var eidx = Math.min(data.req_pg[1], max_pg);
    
    if(jsn.res.apg) {
        var apg = jsn.res.apg;
        var rpg = jsn.res.rpg = {};
        var frm = 0;
        for(var a = sidx; a < eidx; a++) {
            rpg[a+''] = apg.slice(frm, frm + buf.pagesize);
            frm += buf.pagesize;
        }
    }
    
    var rpg = jsn.res.rpg;
    var i, c, p;
    var ncl = [];
    var npg = {};
    for(i = sidx; i < eidx; i++) {
        p = rpg[i+''];
        if(!p) return;
        if( p.length != buf.pagesize && (i + 1 != max_pg || p.length < len % buf.pagesize) ) return;
        npg[i] = p;
        ncl.push(i);
    }
    
    sidx = Math.floor(view.from / buf.pagesize);
    eidx = Math.min(Math.ceil(view.to / buf.pagesize), max_pg);
    for(i = sidx; i < eidx; i++) {
        if(!pg[i] || npg[i]) continue;
        npg[i] = pg[i];
        ncl.unshift(i);
    }
    
    for(i = 0, c = 0; i < cl.length && c < buf.maxpage; i++) {
        p = cl[i];
        if(p >= sidx && p < eidx || p >= max_pg || !pg[p] || npg[p]) continue;
        npg[p] = pg[p];
        ncl.push(p);
        c++;
    }
    
    buf.cachelist = ncl;
    buf.pages = npg;
    //console.log('cache-size:' + buf.cachelist + ':' + sidx + '-' + eidx);
    update.apply(ctx, [len, true]);
}

function load_data()
{
    var data = this.data;
    var view = this.view;
    var buf = view.buf;
    
    if(!this.src.page || typeof(this.src.page) != 'string' || data.reqs[0]) return;
    
    if(buf.pagesize < data.pagesize) {
        buf.pagesize = data.pagesize;
        buf.pages = {};
        buf.cachelist = [];
    }
    
    var sidx = Math.floor(view.from / buf.pagesize);
    var eidx = Math.ceil(view.to / buf.pagesize);
    
    if(view.len) {
        var p = buf.pages[eidx - 1];
        if(sidx == eidx - 1) {
            if( p && (p.length == buf.pagesize || p.length >= view.to % buf.pagesize) ) return;
            
        } else {
            if( p && (p.length == buf.pagesize || p.length >= view.to % buf.pagesize) ) eidx--;
            p = buf.pages[sidx];
            if( p && p.length == buf.pagesize ) sidx++;
            if(sidx >= eidx) return;
            
        }
    }
    
    //console.log('load_data:' + sidx + ':' + eidx)
    data.req_pg = [sidx, eidx];
    data.reqs[0]++;
    data.reqs[1] = $.ajax({context:data.tg, type:this.src.method || 'get', url:this.src.page,
                     data:$.extend({sb:this.cols[view.sortby[0]].fieldname, sd:view.sortby[1], pagesize:buf.pagesize, sidx:sidx, eidx:eidx}, this.src.page_data || this.src.data || {}),
                     success:load_data_cb, dataType:'json',
                     error:ajax_on_error});
}

function seek_cb(jsn, status, req)
{
    var ctx = this.data('tinygrid');
    var data = ctx.data;
    var view = ctx.view;
    var reqs = data.reqs;
    reqs[0]--; reqs[1] = null;
    if(!jsn || !jsn.res) return;
    
    var ridx = jsn.res.ridx;
    var nlen = jsn.res.len;
    if(nlen === undefined) nlen = -1;
    update.apply(ctx, [nlen]);
    select.apply(ctx, [ridx]);
    gotorow.apply(ctx, [ridx]);
}

function seek(kws, sfi)
{
    var data = this.data;
    var view = this.view;
    var reqs = data.reqs;
    
    if(!this.src.rowidx) return;
    
    if(typeof(this.src.rowidx) != 'string') {
        this.src.rowidx.apply(ctx, [kws, sfi]);
        return;
    }
    
    if(reqs[0]) reqs[1].abort();
    if(reqs[0]) { alert('TG -> ajax -> out of sync!'); return; }
    
    reqs[0]++;
    reqs[1] = $.ajax({context:data.tg, type:'get', url:this.src.rowidx,
                     data:$.extend({sb:this.cols[view.sortby[0]].fieldname, sd:view.sortby[1], kws:kws, sfi:sfi}, this.src.page_data || this.src.data || {}),
                     success:seek_cb, dataType:'json',
                     error:ajax_on_error});
}

function refresh_cache_cb(jsn, status, req)
{
    var ctx = this.data('tinygrid');
    var view = ctx.view;
    var reqs = ctx.data.reqs;
    reqs[0]--; reqs[1] = null;
    if(!jsn || !jsn.res) return;
    if(!jsn.res.dataseq || jsn.res.dataseq == view.dataseq) return;
    
    update.apply(ctx, [-1, true, [-1], true]);
    if(ctx.cache_change) ctx.cache_change.apply(ctx, [view.dataseq, jsn.res.dataseq]);
}

function refresh_cache()
{
    var data = this.data;
    var view = this.view;
    var reqs = data.reqs;
    
    if(!this.src.dataseq) return;
    
    if(typeof(this.src.dataseq) != 'string') {
        this.src.dataseq.apply(ctx, []);
        return;
    }
    
    if(reqs[0]) return;
    
    reqs[0]++;
    reqs[1] = $.ajax({context:data.tg, type:'get', url:this.src.dataseq,
                     data:this.src.page_data || this.src.data || {},
                     success:refresh_cache_cb, dataType:'json',
                     error:ajax_on_error});
}

function update(len, force_render, inv_rows, inv_cache, dont_load_data)
{
    var data = this.data;
    var view = this.view;
    var buf = view.buf;
    var rows = data.rows;
    var rlen = rows.length;
    var refresh = false;
    force_render = force_render || data.need_render;
    
    if(data.lockview) { data.lockview++; return }
    
    if(len >= 0 && view.len != len) {
        for(var i = 0; i < rlen; i++) {
            if(rows[i][1] >= len) {
                rows[i][1] = -1;
                rows[i][0].css('top', -data.row_height);
            }
        }
        
        if(len < view.len && buf.pagesize) {
            var sidx = Math.ceil(len / buf.pagesize);
            var eidx = Math.ceil(view.len / buf.pagesize);
            var pgs = buf.pages;
            for(var i = sidx; i < eidx; i++) {
                if(pgs[i]) pgs[i] = null;
            }
        }
        
        view.len = len;
        var b = data.body;
        b.unbind('scroll');
        data.cont.height(view.len * data.row_height);
        b.scroll(i_scroll);
        refresh = true;
    }
    
    if(inv_rows) {
        var pgsz = buf.pagesize;
        var pgs = buf.pages;
    
        if(inv_rows === true || inv_rows.length === 1 && inv_rows[0] === -1) {
            if(inv_cache) { buf.pages = {}; buf.cachelist = []; }
            view.seq++;
            
        } else {
            for(var i = 0; i < inv_rows.length; i++) {
                var j = inv_rows[i];
                var r = rows[ j % rlen];
                if(r[1] == j) r[1] = -1;
                if(inv_cache && pgsz) {
                    var k = Math.floor(j / pgsz);
                    if(pgs[k]) pgs[k] = null;
                }
            }
            
        }
        
    }
    
    if(refresh || force_render) change.apply(this, [force_render, !len || len < 0 && view.len == 0 && dont_load_data]);
}

function render()
{
    var data = this.data;
    var view = this.view;
    data.need_render = false;
    
    from = view.from;
    to = view.to;
    var rows = data.rows;
    var rlen = rows.length;
    var vseq = view.seq;
    var cols = this.cols;
    var clen = cols.length;
    for(var i = from; i < to; i++) {
        var k = i % rlen;
        var s = rows[k];
        var v = null;
        if(s[1] != i || s[2] != vseq) {
            v = getval.apply(this, [i]);
            var c = s[3];
            if(v) {
                s[4] = v;
                for(var y = 0; y < clen; y++) {
                    var d = v[y];
                    if(d === undefined) d = v[y] = cols[y].data;
                    var o = c[y];
                    if(o[1] && o[1].set)
                        o[1].set.apply(o[0], [o[2][0], d])
                    else
                        o[0].text(d);
                }
                s[2] = view.seq;
                
            } else if(s[2] >= 0) {
                s[2] = -1;
                for(var y = 0; y < clen; y++) {
                    var o = c[y];
                    if(o[1] && o[1].set)
                        o[1].set.apply(o[0], [o[2][0], null]);
                    else
                        o[0].text('');
                }
                s[4] = null;
            }
            
            if(s[1] != i) {
                s[0].css('top', i * data.row_height);
                s[1] = i;
            }
            
        }
    }
    
    var ctrl = data.ctrl;
    for(var i in ctrl) {
        var d = ctrl[i];
        var o = d[0];
        var r = d[1];
        var c = d[2];
        if(r < 0) continue;
        if(r >= from && r < to) {
            if(rows[r % rlen][4] !== d[3] && !o.hasClass('tg_ctrl_val_changed')) o.addClass('tg_ctrl_val_changed');
            continue;
        }
        
        o.focusout();
    }
    
    if(data.footer_row.page) data.footer_row.page.text(view.len ? ((from+1) + '-' + to + ' of ' + view.len) : '');
    if(this.render) this.render.call(this);
    
}

function gotorow(n, nofirst)
{
    var data = this.data;
    var view = this.view;
    
    if(n < 0 || n >= view.len) return;
    if(nofirst && n >= view.from && n < view.to) return;
    
    data.body.scrollTop(n * data.row_height);
}

function select(ridx)
{
    var view = this.view;
    var data = this.data;
    var rows = data.rows;
    var hl = data.select_data;
    
    if(ridx < 0 || ridx >= view.len) ridx = -1;
    
    if(hl[1]) {
        var row = data.rows[hl[0] % rows.length];
        if(row[1] != hl[0]) {
            row[0].removeClass('tg_row_select');
            hl[1] = false;
        }
    }
    
    if(ridx == hl[0] && (ridx == -1 || hl[1]) ) return;
    
    if(hl[1]) {
        var row = data.rows[hl[0] % rows.length];
        row[0].removeClass('tg_row_select');
        hl[1] = false;
    }
    
    if(ridx >= 0) {
        if(ridx != hl[0]) {
            hl[0] = ridx;
            hl[2] = false;
        }
        var row = data.rows[ridx % rows.length];
        if(row[1] == ridx && row[2] >= 0) {
            row[0].addClass('tg_row_select');
            hl[1] = true;
            
            if(!hl[2]) {
                hl[2] = true;
                if(this.select) this.select.apply(this, [ridx, row[4]]);
            }
        }
    } else {
        hl[0] = -1;
    }
    
}


function col_hover_in()
{
    var c = $(this).data('tinygrid_col');
    var ridx = c.r;
    var cidx = c.c;
    var ctx = c.ctx;
    var data = ctx.data;
    var view = ctx.view;
    var row = data.rows[ridx];
    if(row[1] < 0 || row[2] < 0) return false;
    var cd = ctx.cols[cidx];
    if(cd.hover[0]) cd.hover[0].apply(ctx, [ridx, cidx, row[4]]);
    
    return false;
}

function col_hover_out()
{
    var c = $(this).data('tinygrid_col');
    var ridx = c.r;
    var cidx = c.c;
    var ctx = c.ctx;
    var data = ctx.data;
    var view = ctx.view;
    var row = data.rows[ridx];
    if(row[1] < 0 || row[2] < 0) return false;
    var cd = ctx.cols[cidx];
    if(cd.hover[1]) cd.hover[1].apply(ctx, [ridx, cidx, row[4]]);
    
    return false;
}

function col_click()
{
    var c = $(this).data('tinygrid_col');
    var ridx = c.r;
    var cidx = c.c;
    var ctx = c.ctx;
    var data = ctx.data;
    var view = ctx.view;
    var row = data.rows[ridx];
    if(row[1] < 0 || row[2] < 0) return false;
    var cf = row[3][cidx];
    var hl = data.select_data;
    var sel = hl[0] == row[1];
    
    ridx = row[1];
    select.apply(ctx, [ridx]);
    
    if(sel && cf[1]) {
        if(cf[1].type == 1) {
            var cc = cf[2];
            cc[1] = row[1];
            cc[2] = cidx;
            cc[3] = row[4];
        }
        if(cf[1].click) {
            if(cf[1].focusout) data.lockview = 1;
            cf[1].click.apply(cf[0], [cf[2][0], row, cidx, ctx]);
        }
    }
    
    if(ctx.click) ctx.click.apply(ctx, [ridx, cidx, row[4]]);
    
    return false;
}

function ctrl_focusout()
{
    var c = $(this).data('tinygrid_ctrl');
    var d = c.d;
    var ctx = c.ctx;
    var data = ctx.data;
    var view = ctx.view;
    var upd = data.lockview - 1;
    data.lockview = 0;
    
    var c_r = d[1];
    var c_c = d[2];
    var c_v = d[3];
    
    d[0].css('top', -100);
    if(d[0].hasClass('tg_ctrl_val_changed')) d[0].removeClass('tg_ctrl_val_changed');
    d[1] = -1;
    d[2] = 0;
    d[3] = null;
    
    if(c_r >= 0) {
        var row = data.rows[ c_r % data.rows.length ];
        if(row[2] >= 0 && c_r == row[1]) {
            var cf = row[3][c_c];
            if(cf[1].focusout) cf[1].focusout.apply(cf[0], [cf[2][0], row, c_c, c_v, ctx]);
        }
    }
    
    if(upd > 0 || data.need_render) update.apply(ctx, [-1, true, [-1], true]);
    
}

function ctrl_keyup(e)
{
    if(e.which == 13 || e.which == 27) {
        e.preventDefault();
        
        if(e.which == 27) {
            var c = $(this).data('tinygrid_ctrl');
            c.d[1] = -1;
        }
        
        $(this).focusout();
    }
}


var g_tgcall = {

'remove': function() {
    for(var i = 0; i < this.length; i++) {
        var ctx = $(this[i]).data('tinygrid');
        if(ctx) remove.apply(ctx, []);
    }
    
    return this;
},

'update': function(a, b, c, d, e) {
    for(var i = 0; i < this.length; i++) {
        var ctx = $(this[i]).data('tinygrid');
        if(ctx) update.apply(ctx, [a, b, c, d, e] );
    }
    
    return this;
},

'view': function() {
    return this.data('tinygrid').view;
},

'goto': function(a, b) {
    for(var i = 0; i < this.length; i++)
        gotorow.apply( $(this[i]).data('tinygrid'), [a, b] );
    return this;
},

'select': function(a) {
    if(a === undefined) {
        return this.data('tinygrid').data.select_data[0];
    } else {
        for(var i = 0; i < this.length; i++)
            select.apply( $(this[i]).data('tinygrid'), [a] );
    }
    return this;
},

'selrow': function() {
    var ctx = this.data('tinygrid');
    var idx = ctx.data.select_data[0];
    if(idx < 0) return null;
    return [idx, getval.apply(ctx, [idx])];
},

'seek': function(a, b) {
    for(var i = 0; i < this.length; i++)
        seek.apply( $(this[i]).data('tinygrid'), [a, b] );
    return this;
},

'refresh': function() {
    for(var i = 0; i < this.length; i++)
        refresh_cache.apply( $(this[i]).data('tinygrid'), [] );
    return this;
},

'src': function(a) {
    if(a === undefined) {
        return this.data('tinygrid').src;
    } else {
        for(var i = 0; i < this.length; i++)
            $.extend($(this[i]).data('tinygrid').src, a);
        return this;
    }
},

'locked': function() {
    return this.data('tinygrid').data.lockview;
}


};

$.fn.tinygrid = function() {
    var k = arguments[0];
    if(k === undefined) k = {}
    
    if(typeof k === "object") {
        for(var i = 0; i < this.length; i++)
            init.apply( $(this[i]), [k] );
        
    } else if (typeof k === "string" && g_tgcall[k] && this.length) {
        return g_tgcall[k].apply(this, Array.prototype.slice.call(arguments, 1));
        
    }
    
    return this;
}

})(jQuery);



(function($) {

function init(a)
{
    this.addClass('tinymenu');
    this.find('> ul li').hover(
        function() { $(this).children('ul').css('display', 'block'); },
        function() { $(this).children('ul').css('display', 'none'); }
    );

    this.find('> ul > li > ul a').click(function() { $(this).closest('ul').css('display', 'none'); });
}

$.fn.tinymenu = function() {
    var k = arguments[0];
    if(k === undefined) k = {}
    
    if(typeof k === "object") {
        for(var i = 0; i < this.length; i++)
            init.apply( $(this[i]), [k] );
        
    }
    
    return this;
}

})(jQuery);


(function($) {

function update_ui(direction, lst)
{
    var ctx = this;
    var data = ctx.data;
    
    var load_data = data.load_data;
    data.load_data = false;
    
    if(!direction)
        ctx.cnt.empty();
    else if(direction === -1) {
        var sc = ctx.self.scrollTop();
        var oh = ctx.cnt.height();
        ctx.cnt.prepend(lst);
        var dh = ctx.cnt.height() - oh;
        dh && ctx.self.scrollTop(sc + dh);
    }
    else
        ctx.cnt.append(lst);
    
    var h = Math.max(ctx.self.height() - 20, 1);
    var p = Math.max( Math.ceil(ctx.cnt.height() * 2.0 / h), ctx.min_padding );
    if(ctx.padding != p) {
        ctx.padding = p;
        ctx.cnt.css('padding', ctx.padding + 'px 0');
    }
    
    scroll.call(ctx.self);
    data.load_data = load_data;
}

function load()
{
    var ctx = this;
    var data = ctx.data;
    var seq = ++data.seq;
    var render = ctx.render;
    
    var args = $.extend({}, ctx.src.args || {});
    var direction = args.direction = data.direction;
    args.token = data.token;
    
    $.get(ctx.src.url, args, function(js) {
        if(seq != data.seq || !js || !js.token) return;
        
        data.token = js.token;
        var lst = js.lst;
        var dlst = [];
        for(var i = 0; i < lst.length; i++) dlst.push(render.call(ctx, lst[i]));
        if(dlst.length) update_ui.call(ctx, direction, dlst);
        
    }, 'json');
}

function setup_timer(direction)
{
    var ctx = this;
    var data = ctx.data;
    if(data.load_timer) window.clearTimeout(data.load_timer);
    data.direction = direction;
    data.load_timer = window.setTimeout(function() { load.call(ctx); }, 300);
}

function refresh(hint) {
    var ctx = this;
    var data = ctx.data;
    data.seq++;
    data.token = undefined;
    
    if(hint === undefined) {
        var lst = ctx.cnt.children('div');
        for(var i = 0; i < lst.length; i++) {
            var o = $(lst[i]);
            if(o.position().top + o.outerHeight(false) >= 0) {
                if(!ctx.src.args) ctx.src.args = {};
                ctx.src.args.hint = o.data('hint');
                break;
            }
        }
    } else {
        if(!ctx.src.args) ctx.src.args = {};
        ctx.src.args.hint = hint;
    }
    
    update_ui.call(ctx, 0);
    
    data.load_data = true;
    setup_timer.call(ctx, 1);
}

function scroll()
{
    var ctx = $(this).data('tinylist');
    
    var i = ctx.self.scrollTop();
    var j = Math.max(0, ctx.cnt.outerHeight(false) - ctx.self.height() - ctx.padding);
    var k = Math.min(j, ctx.padding)
    if(i < k) {
        ctx.self.scrollTop(k);
        ctx.data.load_data && setup_timer.call(ctx, -1);
    } else if(i > j) {
        ctx.self.scrollTop(j);
        ctx.data.load_data && setup_timer.call(ctx, 1);
    }
}

function init(a)
{
    ctx = {};
    $.extend(ctx, a);
    this.addClass('tinylist');
    
    ctx.self = this;
    ctx.cnt = $('<div></div>');
    ctx.data = {seq: 0, load_data: ctx.preload};
    
    this.append(ctx.cnt);
    ctx.min_padding = ctx.padding = Math.ceil((ctx.cnt.outerHeight() - ctx.cnt.height()) / 2);
    
    this.data('tinylist', ctx);

    this.scrollTop(ctx.padding).scroll(scroll);
    if(ctx.data.load_data) setup_timer.call(ctx, 1);
}

var call = {
    'load': function(direction) {
        for(var i = 0; i < this.length; i++)
            setup_timer.call($(this[i]).data('tinylist'), direction);
        return this;
    },
    
    'refresh': function(hint) {
        for(var i = 0; i < this.length; i++)
            refresh.call($(this[i]).data('tinylist'), hint);
        return this;
    }
    
};

$.fn.tinylist = function() {
    var k = arguments[0];
    if(k === undefined) k = {}
    
    if(typeof k === "object") {
        for(var i = 0; i < this.length; i++)
            init.apply( $(this[i]), [k] );
        
    } else if (typeof k === "string" && call[k] && this.length) {
        return call[k].apply(this, Array.prototype.slice.call(arguments, 1));
    
    }

    return this;
}

})(jQuery);





