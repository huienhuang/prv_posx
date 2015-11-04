#include <stdio.h>
#include <Windows.h>

#define BASE_OFFSET(x) (x - 0x00400000)

unsigned long __asm_func_decrypt_ptr;
unsigned long __asm_func_init_ptr__eax;
unsigned long __asm_func_init_ptr;


typedef struct _XSTR
{
	int count;
	int len;
	char buf[1];
} XSTR, *LPXSTR;

__declspec(naked) void __stdcall init()
{
	__asm {
		push ebp;
		mov ebp, esp;
		add esp, -0x10;
		mov eax, __asm_func_init_ptr__eax;
		call __asm_func_init_ptr;
		mov esp, ebp;
		pop ebp;
		ret;
	}
}

__declspec(noinline) void __stdcall decrypt(char *pass, char *in_s, char **out_s)
{
	__asm {
		mov eax, pass;
		mov edx, in_s;
		mov ecx, out_s;
		call __asm_func_decrypt_ptr;
	}
}

LPXSTR new_xstr(LPWSTR str)
{
	int sz = wcstombs(0, str, 4096);
	if(sz < 0) return 0;

	LPXSTR s = (LPXSTR)malloc( sizeof(XSTR) + sz );
	sz = wcstombs(s->buf, str, sz);
	s->buf[sz] = 0;
	s->count = 1;
	s->len = sz;

	return s;
}

void _main()
{
	int argn = 0;
	LPWSTR *argv = CommandLineToArgvW(GetCommandLineW(), &argn);
	if(!argv || argn < 4) return;
	
	LPXSTR passwd = new_xstr(argv[1]);
	LPXSTR in_s = new_xstr(argv[2]);
	char *out_s = 0;

	init();
	decrypt(passwd->buf, in_s->buf, &out_s);

	char buf[256];
	if(out_s && wcstombs(buf, argv[3], sizeof(buf)) > 0) {
		FILE *fp = fopen(buf, "wb");
		fwrite(out_s, strlen(out_s), 1, fp);
		fclose(fp);
	}

	//TerminateProcess(GetCurrentProcess(), 0);
}

int WINAPI DllMain(HINSTANCE hinstDLL,DWORD fdwReason,LPVOID lpvReserved)
{
	//if(AttachConsole(-1)) freopen("CONOUT$", "w", stdout);

	unsigned long base = (unsigned long)GetModuleHandle(0);

	__asm_func_decrypt_ptr = BASE_OFFSET(0x0063FAB4) + base;
	__asm_func_init_ptr__eax = BASE_OFFSET(0x006BCA90) + base;
	__asm_func_init_ptr = BASE_OFFSET(0x004076E8) + base;

	_main();

	TerminateProcess(GetCurrentProcess(), 0);

    return TRUE;
}

