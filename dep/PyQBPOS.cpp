#include <Windows.h>
#include <Python.h>

//Buggy API, Stupid SQLCache Implementation
#import "C:\\Program Files (x86)\\Common Files\\Intuit\\QBPOSSDKRuntime\\QBPOSXMLRPLib.dll"


PyObject *QBPOS_Error;


int WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved)
{

	switch (fdwReason)
	{
	case DLL_PROCESS_ATTACH:
	case DLL_THREAD_ATTACH:
		CoInitialize(0);
		break;
	case DLL_THREAD_DETACH:
		CoUninitialize();
		break;
	}

	return TRUE;
}

struct _CTX {
	QBPOSXMLRPLib::IRequestProcessorPtr req;
	_bstr_t ticket;
};

void CloseConnection(PyObject *cap)
{
	_CTX *ctx = (_CTX *)PyCapsule_GetPointer(cap, 0);
	try {
		ctx->req->EndSession(ctx->ticket);
		ctx->req->CloseConnection();
		ctx->req.Release();
	}
	catch (const _com_error& e) {

	}
	delete ctx;
}

static PyObject *OpenConnection(PyObject *self, PyObject *args)
{
	char *computer_name, *company_file, *file_version;
	char buf[1024];

	if (!PyArg_ParseTuple(args, "sss", &computer_name, &company_file, &file_version)) return NULL;
	sprintf_s(buf, sizeof(buf) / sizeof(buf[0]), "Computer Name=%s;Company Data=%s;Version=%s", computer_name, company_file, file_version);

	_CTX *ctx = new _CTX();

	try {
		ctx->req.CreateInstance(__uuidof(QBPOSXMLRPLib::RequestProcessor));
		ctx->req->OpenConnection("PyQBPOS", "PyQBPOS");
		ctx->ticket = ctx->req->BeginSession(buf);
	}
	catch (const _com_error& e) {
		PyErr_SetString(QBPOS_Error, "OpenConnection->COM Error #1");
		return 0;
	}

	return PyCapsule_New(ctx, 0, CloseConnection);
}

static PyObject *ProcessRequest(PyObject *self, PyObject *args)
{
	wchar_t *buf;
	PyObject *obj;
	_bstr_t res;

	if (!PyArg_ParseTuple(args, "Ou", &obj, &buf)) return NULL;

	_CTX *ctx = (_CTX *)PyCapsule_GetPointer(obj, 0);
	try {
		res = ctx->req->ProcessRequest(ctx->ticket, buf);
		buf = (wchar_t*)res;
	}
	catch (const _com_error& e) {
		PyErr_SetString(QBPOS_Error, "ProcessRequest->COM Error #2");
		return 0;
	}

	return PyUnicode_FromWideChar(buf, wcslen(buf));
}

static PyMethodDef methods[] = {
		{ "OpenConnection", OpenConnection, METH_VARARGS, "OpenConnection(computer_name, company_file, file_version)" },
		{ "ProcessRequest", ProcessRequest, METH_VARARGS, "ProcessRequest(conn, input)" },
		{ NULL, NULL, 0, NULL }
};

PyMODINIT_FUNC initQBPOS()
{
	PyObject *m = Py_InitModule("QBPOS", methods);

	QBPOS_Error = PyErr_NewException("QBPOS.Error", NULL, NULL);
	Py_INCREF(QBPOS_Error);
	PyModule_AddObject(m, "Error", QBPOS_Error);

}
