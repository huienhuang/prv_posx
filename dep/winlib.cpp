#include <stdio.h>
#include <Python.h>
#include <WinSock2.h>
#include <Windows.h>
#include <ws2ipdef.h>
#include <IPHlpApi.h>

typedef int (__stdcall *GET_ARP_LIST_CB)(void *ctx, unsigned long ipv4, long flag, unsigned long long phyaddr);

static int get_arp_list(unsigned long net_id, unsigned long net_mask, GET_ARP_LIST_CB cb, void *cb_ctx)
{
	PMIB_IPNET_TABLE2 ip_tbl = 0;
	unsigned long error;

	Py_BEGIN_ALLOW_THREADS
	error = GetIpNetTable2(AF_INET, &ip_tbl);
	Py_END_ALLOW_THREADS

	if(error != NO_ERROR) return 0;

	net_id &= net_mask;
	unsigned long net_bc = net_id | (~net_mask);
	unsigned long addr;
	unsigned long long phyaddr;
	int count = 0;
	for(unsigned long i = 0; i < ip_tbl->NumEntries; i++) {
		PMIB_IPNET_ROW2 row = ip_tbl->Table + i;

		addr = row->Address.Ipv4.sin_addr.S_un.S_addr;
		if(addr == net_id || addr == net_bc || (addr & net_mask) != net_id) continue;
		phyaddr = 0;
		if(row->InterfaceLuid.Info.IfType == IF_TYPE_ETHERNET_CSMACD && row->PhysicalAddressLength == 6)
			memcpy(&phyaddr, row->PhysicalAddress, 6);
		count++;
		if(!cb(cb_ctx, addr, row->IsUnreachable ? 0 : 1, phyaddr)) break;

	}

	FreeMibTable(ip_tbl);

	return count;
}

static int get_phy_addr(unsigned long ipv4, unsigned long long *phyaddr)
{
	PMIB_IPNET_TABLE2 ip_tbl = 0;
	unsigned long error;

	Py_BEGIN_ALLOW_THREADS
	error = GetIpNetTable2(AF_INET, &ip_tbl);
	Py_END_ALLOW_THREADS

	if(error != NO_ERROR) return -1;

	int ret = 0;
	unsigned long addr;
	for(unsigned long i = 0; i < ip_tbl->NumEntries; i++) {
		PMIB_IPNET_ROW2 row = ip_tbl->Table + i;

		addr = row->Address.Ipv4.sin_addr.S_un.S_addr;
		if(addr == ipv4) {
			*phyaddr = 0;
			if(row->InterfaceLuid.Info.IfType == IF_TYPE_ETHERNET_CSMACD && row->PhysicalAddressLength == 6)
				memcpy(phyaddr, row->PhysicalAddress, 6);
			ret = 1;
			break;
		}
	}

	FreeMibTable(ip_tbl);

	return ret;
}

static PyObject* winlib__get_phy_addr(PyObject *self, PyObject *args)
{
	unsigned long net_id;
	unsigned long long phyaddr;
	if(!PyArg_ParseTuple(args, "k", &net_id)) return 0;

	int ret = get_phy_addr(net_id, &phyaddr);
	return Py_BuildValue("iK", ret, phyaddr);
}

static int __stdcall arp_cb(PyObject *lst, unsigned long ipv4, long flag, unsigned long long phyaddr)
{
	PyObject *t = Py_BuildValue("kiK", ipv4, flag, phyaddr);
	PyList_Append(lst, t);
	Py_DecRef(t);
	return 1;
}

static PyObject* winlib__get_arp_list(PyObject *self, PyObject *args)
{
	unsigned long net_id;
	unsigned long net_mask;
	if(!PyArg_ParseTuple(args, "kk", &net_id, &net_mask)) return 0;

	PyObject *lst = PyList_New(0);
	get_arp_list(net_id, net_mask, (GET_ARP_LIST_CB)arp_cb, lst);
	return lst;
}


static int cn_poly(double p[2], double v[][2], int n)
{
	int cn = 0;
	for(int i = 0; i < n - 1; i++) {
		if(v[i][1] <= p[1] && v[i + 1][1] > p[1] || v[i][1] > p[1] && v[i + 1][1] <= p[1]) {
			if(p[0] < (p[1] - v[i][1]) / (v[i + 1][1] - v[i][1]) * (v[i + 1][0] - v[i][0]) + v[i][0]) ++cn;
		}
	}

	return cn & 1;
}

static PyObject* winlib__cn_poly(PyObject *self, PyObject *args)
{
	static double v[512][2];
	double p[2];
	int n;
	const char *s;
	if(!PyArg_ParseTuple(args, "dds#", p, p + 1, &s, &n)) return 0;

	n = min(sizeof(v), n);
	memcpy((void*)v, (void*)s, n);

	return PyInt_FromLong( cn_poly(p, v, n / sizeof(v[0])) );
}



#define BOUNDARY_MSZ 64
#define BOUNDARY_PTS_MSZ 96

typedef struct _Boundary
{
	double min_pt[2];
	double max_pt[2];

	double pts[BOUNDARY_PTS_MSZ][2];
	int pts_sz;

} Boundary;

static Boundary boundary[BOUNDARY_MSZ];
static int boundary_sz = 0;

static PyObject* winlib__load_boundary(PyObject *self, PyObject *args)
{
	Boundary *b;
	PyObject *o, *p;
	int n, m;
	char *s;
	boundary_sz = 0;

	if(!PyArg_ParseTuple(args, "O", &o) || !PyTuple_Check(o)) return 0;
	n = min(BOUNDARY_MSZ, PyTuple_GET_SIZE(o));

	for(int i = 0; i < n; i++) {
		p = PyTuple_GET_ITEM(o, i);
		if(!PyString_Check(p) || PyString_AsStringAndSize(p, &s, &m) < 0) return 0;
		
		b = boundary + i;
		m = min(m, sizeof(b->pts));
		
		memcpy(b->pts, s, m);

		m = m / sizeof(b->pts[0]);
		if(m <= 0) return 0;

		b->min_pt[0] = b->max_pt[0] = b->pts[0][0];
		b->min_pt[1] = b->max_pt[1] = b->pts[0][1];

		for(int j = 1; j < m; j++) {
			if(b->pts[j][0] < b->min_pt[0])
				b->min_pt[0] = b->pts[j][0];
			else if(b->pts[j][0] > b->max_pt[0])
				b->max_pt[0] = b->pts[j][0];

			if(b->pts[j][1] < b->min_pt[1])
				b->min_pt[1] = b->pts[j][1];
			else if(b->pts[j][1] > b->max_pt[1])
				b->max_pt[1] = b->pts[j][1];
		}

		b->pts_sz = m;
	}

	boundary_sz = n;

	Py_RETURN_NONE;
}

static PyObject* winlib__find_boundary(PyObject *self, PyObject *args)
{
	double p[2];
	if(!PyArg_ParseTuple(args, "dd", p, p + 1)) return 0;

	Boundary *b;
	int idx = -1;
	for(int i = 0; i < boundary_sz; i++) {
		b = boundary + i;
		if(p[0] < b->min_pt[0] || p[0] > b->max_pt[0] || p[1] < b->min_pt[1] || p[1] > b->max_pt[1]) continue;
		if(cn_poly(p, b->pts, b->pts_sz)) {
			idx = i;
			break;
		}
	}

	return PyInt_FromLong(idx);
}

static PyMethodDef winlib_methods[] =
{
	{"load_boundary", winlib__load_boundary, METH_VARARGS},
	{"find_boundary", winlib__find_boundary, METH_VARARGS},
	{"cn_poly", winlib__cn_poly, METH_VARARGS},
	{"get_arp_list", winlib__get_arp_list, METH_VARARGS},
	{"get_phy_addr", winlib__get_phy_addr, METH_VARARGS},
    {NULL, NULL, 0}
};

PyMODINIT_FUNC initwinlib()
{
	Py_InitModule("winlib", winlib_methods);
}
