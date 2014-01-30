//v2 - 06/29/2013 - always show scroll-y


(function($) {


var g_tg_ctrl = {
'edit': {
    type: 1,
    init: function() {
        return this.append('<input type="text" class="tg_col_c_text" />').find('> .tg_col_c_text');
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
        return this.append('<select class="tg_col_c_select"></select>').find('> .tg_col_c_select');
    },
    click: function(co, row, cidx, ctx) {
        var ed = row[4][cidx];
        var optd = ed[1];
        var opte = co.find('> option');
        
        if(opte.length < optd.length) {
            var s = '';
            for(var i = opte.length; i < optd.length; i++) s += '<option></option>';
            opte = co.append(s).find('> option');
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
        click: null,
        select: null,
        change: null,
        render: null,
        getval: null,
        ctrl_change: null,
        ctrls: {},
        cache_change: null,
        footer_html: '<div id="tgft_id_page" class="tgft_cls_elem"></div>',
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
    s = '<div class="tg_row tg_header">Header</div><div class="tg_body"><div></div><div></div></div><div class="tg_row tg_footer">'+ctx.footer_html+'</div>';
    this.addClass('tinygrid').html(s);
    var tg_header = this.find('> div.tg_header');
    var tg_body = this.find('> div.tg_body');
    var tg_cont = tg_body.find('> div:nth-child(1)');
    var tg_meter = tg_body.find('> div:nth-child(2)');
    var tg_footer = this.find('> div.tg_footer');
    var row_height = tg_header.outerHeight(false);
    this.css('padding', row_height+'px 0');
    
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
    var eh = tg_header.width(tw).html(h).find('> .tg_col').click(header_col_click);
    var header_row = [];
    for(var i = 0; i < eh.length; i++) {
        var ec = $(eh[i]);
        ec.data('tinygrid_col_hdr', {c:i, ctx:ctx});
        header_row[i] = ec;
    }
    header_row[ ctx.sortby[0] ].addClass(ctx.sortby[1] ? 'tg_col_sort_desc' : 'tg_col_sort_asc');
    
    var footer_row = {};
    var ef = tg_footer.find('.tgft_cls_elem');
    for(var i = 0; i < ef.length; i++) {
        var ec = $(ef[i]);
        footer_row[ ec.attr('id').substr(8) ] = ec;
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
        reqs:[null, null, null],
        lockview:0,
        need_render:false,
        };
        
    this.data('tinygrid', ctx);
    tg_body.data('tinygrid', ctx).scroll(i_scroll);
    
    update.apply(ctx, [ctx.len, true]);
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
    for(var i = 0; i < clsz; i++) {
        var w = cols[i].width;
        var a = [0, parseInt(w)];
        
        if(typeof w == 'string' && w.indexOf('%')) {
            a[0] = 1;
            ps += a[1];
        } else
            cw -= a[1];
        
        ws[i] = a;
    }
    
    if(cw <= 0 || ps <= 0) return;
    
    var tw = 0;
    var c = '';
    for(var i = 0; i < clsz; i++) {
        var a = ws[i];
        if(a[0]) a[1] = Math.floor(a[1] / ps * cw);
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
            var ct = cols[j].ctrlname;
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
        autowidth(ctx);
    }
    
    var height = data.tg.height();
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
    
    if(!dont_load_data) load_data.call(ctx);
    if(data.select_data[0] >= 0) select.apply(ctx, [data.select_data[0]])
}

function load_data_err(req)
{
    var ctx = this.data('tinygrid');
    var reqs = ctx.data.reqs;
    
    if(!reqs[0] || req !== reqs[0]) return;
    reqs[0] = null;
    console.log('>> load_data_err ajax error');
}

function load_data_cb(jsn, status, req)
{
    var ctx = this.data('tinygrid');
    var data = ctx.data;
    var reqs = data.reqs;
    if(!reqs[0] || req !== reqs[0]) return;
    reqs[0] = null;
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
    var rpg = jsn.res.rpg;
    var sidx = data.req_pg[0];
    var max_pg = Math.ceil(len / buf.pagesize);
    var eidx = Math.min(data.req_pg[1], max_pg);
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
    data.reqs[0] = $.ajax({context:data.tg, type:'get', url:this.src.page,
                     data:$.extend({sb:this.cols[view.sortby[0]].fieldname, sd:view.sortby[1], pagesize:buf.pagesize, sidx:sidx, eidx:eidx}, this.src.page_data || this.src.data || {}),
                     success:load_data_cb, dataType:'json',
                     error:load_data_err});
}

function seek_error(req)
{
    var ctx = this.data('tinygrid');
    var reqs = ctx.data.reqs;
    if(!reqs[1] || req !== reqs[1]) return;
    reqs[1] = null;
    console.log('>> seek_error ajax error');
}

function seek_cb(jsn, status, req)
{
    var ctx = this.data('tinygrid');
    var data = ctx.data;
    var view = ctx.view;
    var reqs = data.reqs;
    if(!reqs[1] || req !== reqs[1]) return;
    reqs[1] = null;
    if(!jsn || !jsn.res) return;
    
    var ridx = jsn.res.ridx;
    var nlen = jsn.res.len;
    if(nlen !== undefined) nlen = -1;
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
    
    if(reqs[1]) { reqs[1].abort(); reqs[1] = null; }
    
    reqs[1] = $.ajax({context:data.tg, type:'get', url:this.src.rowidx,
                     data:$.extend({sb:this.cols[view.sortby[0]].fieldname, sd:view.sortby[1], kws:kws, sfi:sfi}, this.src.page_data || this.src.data || {}),
                     success:seek_cb, dataType:'json',
                     error:seek_error});
}

function refresh_cache_error(req)
{
    var ctx = this.data('tinygrid');
    var reqs = ctx.data.reqs;
    if(!reqs[2] || req !== reqs[2]) return;
    reqs[2] = null;
    console.log('>> refresh_cache_error ajax error');
    
}

function refresh_cache_cb(jsn, status, req)
{
    var ctx = this.data('tinygrid');
    var view = ctx.view;
    var reqs = ctx.data.reqs;
    if(!reqs[2] || req !== reqs[2]) return;
    reqs[2] = null;
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
    
    if(reqs[2]) {reqs[2].abort(); reqs[2]=null;}
    
    reqs[2] = $.ajax({context:data.tg, type:'get', url:this.src.dataseq,
                     data:this.src.page_data || this.src.data || {},
                     success:refresh_cache_cb, dataType:'json',
                     error:refresh_cache_error});
    
}

function update(len, force_render, inv_rows, inv_cache)
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
    
        for(var i = 0; i < inv_rows.length; i++) {
            var j = inv_rows[i];
            if(j < 0) {
                if(data.reqs[0]) { data.reqs[0].abort(); data.reqs[0] = null; }
                if(inv_cache) { buf.pages = {}; buf.cachelist = []; }
                view.seq++;
                break;
            }
            var r = rows[ j % rlen];
            if(r[1] == j) r[1] = -1;
            if(inv_cache && pgsz) {
                var k = Math.floor(j / pgsz);
                if(pgs[k]) pgs[k] = null;
            }
        }
    }
    
    if(refresh || force_render) change.apply(this, [force_render, !len]);
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
    
    if(data.footer_row.page && view.len) data.footer_row.page.text((from+1) + '-' + to + ' of ' + view.len);
    
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

'update': function(a, b, c, d) {
    for(var i = 0; i < this.length; i++) {
        var ctx = $(this[i]).data('tinygrid');
        if(ctx) update.apply(ctx, [a, b, c, d] );
    }
    
    return this;
},

'view': function(a, b, c, d) {
    return this.data('tinygrid').view;
},

'goto': function(a, b, c, d) {
    for(var i = 0; i < this.length; i++)
        gotorow.apply( $(this[i]).data('tinygrid'), [a, b] );
    return this;
},

'select': function(a, b, c, d) {
    if(a === undefined) {
        return this.data('tinygrid').data.select_data[0];
    } else {
        for(var i = 0; i < this.length; i++)
            select.apply( $(this[i]).data('tinygrid'), [a] );
    }
    return this;
},

'selrow': function(a, b, c, d) {
    var ctx = this.data('tinygrid');
    var idx = ctx.data.select_data[0];
    if(idx < 0) return null;
    return [idx, getval.apply(ctx, [idx])];
},

'seek': function(a, b, c, d) {
    for(var i = 0; i < this.length; i++)
        seek.apply( $(this[i]).data('tinygrid'), [a, b] );
    return this;
},

'refresh': function(a, b, c, d) {
    for(var i = 0; i < this.length; i++)
        refresh_cache.apply( $(this[i]).data('tinygrid'), [] );
    return this;
},

'src': function(a, b, c, d) {
    for(var i = 0; i < this.length; i++)
        $.extend($(this[i]).data('tinygrid').src, a);
    return this;
},

'locked': function(a, b, c, d) {
    return this.data('tinygrid').data.lockview;
}


};

$.fn.tinygrid = function(k, v0, v1, v2, v3) {
    if(k === undefined) k = {}
    
    if(typeof k === "object") {
        for(var i = 0; i < this.length; i++)
            init.apply( $(this[i]), [k] );
        
    } else if (typeof k === "string" && g_tgcall[k]) {
        return g_tgcall[k].apply(this, [v0, v1, v2, v3]);
        
    }
    
    return this;
}

})(jQuery);


