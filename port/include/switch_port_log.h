#pragma once
#ifdef __SWITCH__
#include <stdio.h>
#include <stdarg.h>
/* 전역 파일 핸들: 모든 TU가 공유 (static이면 TU마다 별개 fopen 발생) */
extern FILE *g_pl_file;
static void plog(const char *fmt, ...) {
    if (!g_pl_file) g_pl_file = fopen("sdmc:/switch/ge007/port.log", "a");
    if (!g_pl_file) return;
    va_list ap; va_start(ap, fmt);
    vfprintf(g_pl_file, fmt, ap); va_end(ap);
    fputc('\n', g_pl_file); fflush(g_pl_file);
}
#else
static void plog(const char *fmt, ...) { (void)fmt; }
#endif
