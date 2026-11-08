/* Optional workspace compatibility: normalize only this process's own
 * /proc/PID/exe entry. No proof-checking functions are replaced. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
ssize_t readlink(const char *path, char *buf, size_t size) {
    ssize_t (*original)(const char *, char *, size_t) = dlsym(RTLD_NEXT, "readlink");
    char own[80];
    snprintf(own, sizeof own, "/proc/%ld/exe", (long)getpid());
    if (strcmp(path, own) == 0) return original("/proc/self/exe", buf, size);
    return original(path, buf, size);
}
