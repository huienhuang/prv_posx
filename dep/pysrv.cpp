#include <stdio.h>
#include <Windows.h>
#include <Python.h>

int g_started = 0;
int g_stop_pending = 0;
SERVICE_STATUS_HANDLE g_srv_status_handle = 0;
SERVICE_STATUS g_srv_status = {
	SERVICE_WIN32_OWN_PROCESS,
	SERVICE_START_PENDING,
	SERVICE_ACCEPT_STOP,
	NO_ERROR,
	0,
	0,
	0
};
HANDLE g_pythread_handle = 0;
PyObject *g_py_module = 0;
PyObject *g_py_main = 0;

void set_srv_status(DWORD state, DWORD error)
{
	static int chk_pt = 1;
	g_srv_status.dwCurrentState = state;
	g_srv_status.dwCheckPoint = (state == SERVICE_RUNNING || state == SERVICE_STOPPED) ? 0 : chk_pt++;
	g_srv_status.dwWin32ExitCode = error;

	SetServiceStatus(g_srv_status_handle, &g_srv_status);
}

DWORD WINAPI pythread(void *param)
{

	PyObject *arg = PyTuple_New(0);
	PyObject *ret = PyObject_CallObject(g_py_main, arg);
	Py_DECREF(arg);
	if(!ret)
		PyErr_Print();
	else
		Py_DECREF(ret);

	return 0;
}

void start_pythread(int argc, char **argv)
{
	set_srv_status(SERVICE_START_PENDING, NO_ERROR);
	g_pythread_handle = CreateThread(0, 0, pythread, 0, 0, 0);
	set_srv_status(SERVICE_RUNNING, NO_ERROR);
	//set_srv_status(SERVICE_STOPPED, NO_ERROR);
}

void stop_pythread()
{
	g_stop_pending = 1;
	set_srv_status(SERVICE_STOP_PENDING, NO_ERROR);
	while(g_pythread_handle && WaitForSingleObject(g_pythread_handle, 1000) == WAIT_TIMEOUT) set_srv_status(SERVICE_STOP_PENDING, NO_ERROR);
	set_srv_status(SERVICE_STOPPED, NO_ERROR);
	g_pythread_handle = 0;
}

int install_service(char *srv_name, char *script, char *log)
{
	char path[MAX_PATH * 2];
	if(!GetModuleFileName(0, path, MAX_PATH)) { printf("Error:GetModuleFileName\n"); return 0; }
	
	strcat(path, " \""); strcat(path, script); strcat(path, "\" \"");
	if(log)
		strcat(path, log);
	else {
		strcat(path, script);
		strcat(path, ".log.txt");
	}
	strcat(path, "\"");

	SC_HANDLE scmgr = OpenSCManager(0, 0, SC_MANAGER_CONNECT|SC_MANAGER_CREATE_SERVICE);
	if(!scmgr) { printf("Error:OpenSCManager\n"); return 0; }

	SC_HANDLE scsrv = CreateService(
		scmgr,
		srv_name,
		0,
        SERVICE_QUERY_STATUS,
        SERVICE_WIN32_OWN_PROCESS,
        SERVICE_AUTO_START,
        SERVICE_ERROR_NORMAL,
        path,
        0,
        0,
        0,
        0,
        0
		);
	if(!scsrv) { 
		printf("Error:CreateService[%08X]\n", GetLastError());
		CloseServiceHandle(scmgr);
		return 0;
	}

	CloseServiceHandle(scsrv);
	CloseServiceHandle(scmgr);
	return 1;
}

int remove_service(char *srv_name)
{
	SERVICE_STATUS status = {};

	SC_HANDLE scmgr = OpenSCManager(0, 0, SC_MANAGER_CONNECT);
	if(!scmgr) { printf("Error:OpenSCManager\n"); return 0; }

	SC_HANDLE scsrv = OpenService(scmgr, srv_name, SERVICE_STOP|SERVICE_QUERY_STATUS|DELETE);
	if(!scsrv) { 
		printf("Error:OpenService\n");
		goto error_0;
	}

	if (ControlService(scsrv, SERVICE_CONTROL_STOP, &status)) {
		Sleep(1000);
		while(QueryServiceStatus(scsrv, &status) && status.dwCurrentState == SERVICE_STOP_PENDING) Sleep(500);
	} 

	if (!DeleteService(scsrv)) {
		printf("Error:DeleteService\n");
		goto error_1;
	}

	CloseServiceHandle(scsrv);
	CloseServiceHandle(scmgr);
	return 1;

error_1:
	CloseServiceHandle(scsrv);
error_0:
	CloseServiceHandle(scmgr);
	return 0;
}

VOID WINAPI srv_ctrl_handler(DWORD dwCtrl)
{
	switch (dwCtrl)
	{
	case SERVICE_CONTROL_STOP:
		stop_pythread();
		break;
	default: break;
	}
}

VOID WINAPI srv_main(DWORD dwArgc, LPTSTR *lpszArgv)
{
	if(g_started) return;
	g_started = 1;

	g_srv_status_handle = RegisterServiceCtrlHandler("", srv_ctrl_handler);
	start_pythread(dwArgc, lpszArgv);
}

static PyObject* pysrv_stop_pending(PyObject *self, PyObject *args)
{
	return PyInt_FromLong(g_stop_pending);
}

static PyMethodDef pysrv_methods[] =
{
	{"stop_pending", pysrv_stop_pending, METH_NOARGS},
    {NULL, NULL, 0}
};

int main(int argc, char *argv[])
{
	if(argc < 2) return 1;
	char *v = argv[1];
	if(v[0] == L'-') {
		if(v[1] == L'i') {
			if(argc >= 3)
				return install_service(v + 2, argv[2], argc >= 4 ? argv[3] : 0);

		} else if(v[1] == L'r')
			return remove_service(v + 2);
		
		printf("Error:invalid argv");

	} else if(argc == 3) {
		char buf[MAX_PATH];
		strcpy(buf, argv[1]);
		char *mnz = strrchr(buf, '\\');
		if(!mnz) return 1;
		*mnz = 0; mnz++;
		*strrchr(mnz, '.') = 0;

		Py_Initialize();

		PyObject *f = PyFile_FromString(argv[2], "w");
		PyFile_SetBufSize(f, 0);
		PySys_SetObject("stdout", f);
		PySys_SetObject("stderr", f);
		Py_DECREF(f);

		PyObject *path = PySys_GetObject("path");
		PyObject *s = PyString_FromString(buf);
		PyList_Insert(path, 0, s);
		Py_DECREF(s);

		Py_InitModule("pysrv", pysrv_methods);

		g_py_module = PyImport_ImportModule(mnz);
		if(!g_py_module) {
			PySys_WriteStderr("Error:PyImport_ImportModule\n");
			Py_Finalize();
			return 1;
		}
		g_py_main = PyObject_GetAttrString(g_py_module, "main");
		if(!g_py_main || !PyCallable_Check(g_py_main)) {
			PySys_WriteStderr("Error:PyObject_GetAttrString\n");
			if(g_py_main) Py_DECREF(g_py_main);
			Py_DECREF(g_py_module);
			Py_Finalize();
			return 1;
		}

		SERVICE_TABLE_ENTRY srv_tbl[] = {
			{"", srv_main},
			{0, 0}
		};
		StartServiceCtrlDispatcher(srv_tbl);

		if(g_pythread_handle) {
			g_stop_pending = 1;
			WaitForSingleObject(g_pythread_handle, INFINITE);
		}

		Py_DECREF(g_py_main);
		Py_DECREF(g_py_module);
		Py_Finalize();

		return 0;
	}

	return 1;
}

