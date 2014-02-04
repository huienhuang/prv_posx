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

static PyMethodDef winlib_methods[] =
{
	{"get_arp_list", winlib__get_arp_list, METH_VARARGS},
	{"get_phy_addr", winlib__get_phy_addr, METH_VARARGS},
    {NULL, NULL, 0}
};

PyMODINIT_FUNC initwinlib()
{
	Py_InitModule("winlib", winlib_methods);
}
